from datetime import datetime, timezone

import httpx

from app.core.config import Settings
from app.core.logging import logger
from app.domain.schemas import ProspectIn


class FinnApiClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def is_configured(self) -> bool:
        return bool(self.settings.finn_api_key and self.settings.finn_org_id)

    def fetch_since(self, since: datetime | None = None) -> list[ProspectIn]:
        if not self.is_configured():
            logger.warning("finn_api_not_configured_fallback")
            return []

        headers = {
            "X-API-KEY": self.settings.finn_api_key or "",
            "X-ORG-ID": self.settings.finn_org_id or "",
        }
        params = {
            "price_from": self.settings.min_price_nok,
            "price_to": self.settings.max_price_nok,
            "sort": "published-desc",
            "regions": ",".join(self.settings.target_regions),
        }
        if since:
            params["published_after"] = since.astimezone(timezone.utc).isoformat()

        try:
            with httpx.Client(timeout=20) as client:
                resp = client.get(f"{self.settings.finn_api_base_url}/realestate-homes", headers=headers, params=params)
                resp.raise_for_status()
                payload = resp.json()
        except Exception as exc:  # graceful fallback
            logger.error("finn_api_fetch_failed", error=str(exc))
            return []

        items = payload.get("items", []) if isinstance(payload, dict) else []
        prospects: list[ProspectIn] = []
        for item in items:
            prospects.append(
                ProspectIn(
                    source="finn_api",
                    external_id=str(item.get("id") or item.get("ad_id") or ""),
                    title=item.get("title") or "FINN bolig",
                    url=item.get("url") or "",
                    price_nok=item.get("price") or item.get("asking_price"),
                    common_costs_monthly=item.get("common_costs"),
                    size_m2=item.get("area_p") or item.get("size_m2"),
                    address=item.get("address"),
                    municipality=item.get("municipality"),
                    region=item.get("region"),
                    lat=item.get("lat"),
                    lon=item.get("lon"),
                    property_type=item.get("property_type"),
                    ownership_type=item.get("ownership_type"),
                    bedrooms=item.get("bedrooms"),
                    energy_label=item.get("energy_label"),
                    build_year=item.get("build_year"),
                    listing_text=item.get("description"),
                    published_at=_parse_datetime(item.get("published_at")),
                )
            )
        return [p for p in prospects if p.external_id and p.url]


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
