import email
import imaplib
import re
from datetime import datetime
from email.message import Message
from email.utils import parsedate_to_datetime

from app.core.config import Settings
from app.core.logging import logger
from app.domain.schemas import ProspectIn

FINN_LINK_RE = re.compile(r"https?://(?:www\.)?finn\.no/realestate/homes/ad\.html\?finnkode=([0-9]+)")
PRICE_RE = re.compile(r"(?:kr\.?\s*)?([0-9\s\.]{3,})")


class EmailIngest:
    def __init__(self, settings: Settings):
        self.settings = settings

    def is_configured(self) -> bool:
        return bool(self.settings.imap_username and self.settings.imap_password)

    def fetch_since(self, since: datetime | None = None) -> list[ProspectIn]:
        if not self.is_configured():
            logger.warning("imap_not_configured")
            return []

        criteria = [f'FROM "{self.settings.email_sender_filter}"']
        if since:
            criteria.append(f'SINCE "{since.strftime("%d-%b-%Y")}"')
        query = f"({' '.join(criteria)})"

        with imaplib.IMAP4_SSL(self.settings.imap_host, self.settings.imap_port) as mail:
            mail.login(self.settings.imap_username, self.settings.imap_password)
            mail.select(self.settings.imap_mailbox)
            status, data = mail.search(None, query)
            if status != "OK":
                return []

            ids = data[0].split()
            prospects: list[ProspectIn] = []
            for msg_id in ids:
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                raw = msg_data[0][1]
                message = email.message_from_bytes(raw)
                prospects.extend(self._parse_message(message))
            return prospects

    def _parse_message(self, msg: Message) -> list[ProspectIn]:
        text = _extract_text(msg)
        published_at = None
        try:
            published_at = parsedate_to_datetime(msg.get("Date")) if msg.get("Date") else None
        except Exception:
            published_at = None

        prospects: list[ProspectIn] = []
        for match in FINN_LINK_RE.finditer(text):
            finnkode = match.group(1)
            url = match.group(0)
            snippet = text[max(0, match.start() - 180): match.start() + 300]
            price = _try_parse_price(snippet)
            title = _extract_title(snippet) or f"FINN annonse {finnkode}"
            prospects.append(
                ProspectIn(
                    source="email",
                    external_id=finnkode,
                    title=title,
                    url=url,
                    price_nok=price,
                    listing_text=snippet,
                    published_at=published_at,
                )
            )
        return prospects


def _extract_text(msg: Message) -> str:
    if msg.is_multipart():
        out = []
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type in {"text/plain", "text/html"}:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                out.append(payload.decode(charset, errors="ignore"))
        return "\n".join(out)
    payload = msg.get_payload(decode=True) or b""
    return payload.decode(msg.get_content_charset() or "utf-8", errors="ignore")


def _try_parse_price(text: str) -> float | None:
    m = PRICE_RE.search(text)
    if not m:
        return None
    digits = re.sub(r"\D", "", m.group(1))
    return float(digits) if digits else None


def _extract_title(text: str) -> str | None:
    line = text.strip().splitlines()[0] if text.strip() else ""
    return line[:240] if line else None
