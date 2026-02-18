from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.core.config import Settings
from app.domain.models import Prospect

try:
    from weasyprint import HTML
except Exception:  # pragma: no cover
    HTML = None


def generate_weekly_report(prospects: list[Prospect], settings: Settings) -> tuple[str, str | None, str]:
    out_dir = Path(settings.report_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sorted_p = sorted(prospects, key=lambda p: p.score or 0, reverse=True)
    top = sorted_p[:5]
    bubble = sorted_p[5:10]

    env = Environment(loader=FileSystemLoader("app/templates"))
    tpl = env.get_template("weekly_report.html.j2")
    html = tpl.render(
        generated_at=datetime.utcnow().isoformat(timespec="seconds"),
        ingest_mode=settings.ingest_mode,
        top_prospects=top,
        bubble_prospects=bubble,
    )

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    html_path = out_dir / f"weekly_report_{ts}.html"
    html_path.write_text(html, encoding="utf-8")

    pdf_path = None
    if HTML:
        pdf_path = out_dir / f"weekly_report_{ts}.pdf"
        HTML(string=html, base_url=".").write_pdf(pdf_path)

    return str(html_path), str(pdf_path) if pdf_path else None, html
