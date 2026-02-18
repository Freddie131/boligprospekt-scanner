from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.logging import logger
from app.domain.models import DataSource, JobRun, PriceHistory, Prospect, ProspectStatus
from app.domain.schemas import ProspectIn
from app.ingest.email_ingest import EmailIngest
from app.ingest.finn_api_client import FinnApiClient
from app.services.geo import haversine_km, rough_travel_minutes
from app.services.report import generate_weekly_report
from app.services.scoring import calculate_score


class WeeklyJobService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings

    def run(self) -> JobRun:
        run = JobRun(job_name="weekly", status="running")
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        try:
            since = datetime.utcnow() - timedelta(days=8)
            prospects_in = self._ingest(since)
            persisted = self._upsert_prospects(prospects_in)
            self._score_prospects(persisted)

            all_active = self.db.scalars(select(Prospect).where(Prospect.status != ProspectStatus.archived)).all()
            html_path, pdf_path, _ = generate_weekly_report(all_active, self.settings)

            run.status = "success"
            run.records_ingested = len(prospects_in)
            run.report_html_path = html_path
            run.report_pdf_path = pdf_path
            run.finished_at = datetime.utcnow()
            self.db.commit()
            return run
        except Exception as exc:
            run.status = "failed"
            run.metadata_json = {"error": str(exc)}
            run.finished_at = datetime.utcnow()
            self.db.commit()
            logger.exception("weekly_job_failed", error=str(exc))
            raise

    def _ingest(self, since: datetime) -> list[ProspectIn]:
        mode = self.settings.ingest_mode
        if mode == "finn_api":
            data = FinnApiClient(self.settings).fetch_since(since)
            if data:
                return data
            logger.warning("finn_api_empty_fallback_to_email")
            data = EmailIngest(self.settings).fetch_since(since)
            return data if data else mock_prospects()
        if mode == "email":
            data = EmailIngest(self.settings).fetch_since(since)
            return data if data else mock_prospects()
        return mock_prospects()

    def _upsert_prospects(self, prospects: list[ProspectIn]) -> list[Prospect]:
        result: list[Prospect] = []
        for p in prospects:
            src = DataSource(p.source)
            existing = self.db.scalar(select(Prospect).where(Prospect.source == src, Prospect.external_id == p.external_id))
            if existing:
                for field, value in p.model_dump().items():
                    if value is not None and hasattr(existing, field):
                        setattr(existing, field, value)
                prospect = existing
            else:
                payload = p.model_dump()
                payload["source"] = src
                prospect = Prospect(**payload)
                self.db.add(prospect)

            if p.price_nok:
                self.db.add(PriceHistory(prospect=prospect, price_nok=p.price_nok))
            if not p.price_nok or not p.size_m2:
                prospect.status = ProspectStatus.needs_manual_enrichment
            else:
                prospect.status = ProspectStatus.active
            result.append(prospect)

        self.db.commit()
        for prospect in result:
            self.db.refresh(prospect)
        return result

    def _score_prospects(self, prospects: list[Prospect]) -> None:
        for p in prospects:
            if p.lat is not None and p.lon is not None:
                distance = haversine_km(self.settings.grimstad_lat, self.settings.grimstad_lon, p.lat, p.lon)
                travel = rough_travel_minutes(distance)
            else:
                distance = None
                travel = None

            score, detail = calculate_score(p, self.settings)
            detail["distance_km"] = round(distance, 1) if distance else None
            detail["travel_minutes_est"] = travel
            detail["why_high_score"] = _compose_reason(detail)

            p.score = score
            p.risk_flags = detail.get("risk_flags", [])
            p.metrics = detail
        self.db.commit()


def _compose_reason(detail: dict) -> str:
    reasons = []
    if detail.get("proximity", 0) >= 30:
        reasons.append("sterk nærhet til Grimstad")
    if detail.get("cashflow", 0) >= 35:
        reasons.append("god estimert netto cashflow")
    if detail.get("value_add", 0) >= 30:
        reasons.append("tydelig verdiskapingspotensial")
    return ", ".join(reasons) if reasons else "akseptabel totalprofil"


def mock_prospects() -> list[ProspectIn]:
    now = datetime.utcnow()
    return [
        ProspectIn(
            source="mock",
            external_id="mock-1",
            title="Enebolig nær UiA Grimstad",
            url="https://example.com/mock-1",
            price_nok=3_450_000,
            common_costs_monthly=0,
            size_m2=110,
            address="Grimstad sentrum",
            municipality="Grimstad",
            region="Agder",
            lat=58.341,
            lon=8.595,
            property_type="Enebolig",
            ownership_type="Selveier",
            bedrooms=3,
            energy_label="D",
            build_year=1978,
            listing_text="Oppussingsobjekt med moderniseringsbehov men god planløsning.",
            published_at=now,
        ),
        ProspectIn(
            source="mock",
            external_id="mock-2",
            title="Leilighet i Arendal med utleiemulighet",
            url="https://example.com/mock-2",
            price_nok=2_750_000,
            common_costs_monthly=2100,
            size_m2=72,
            municipality="Arendal",
            region="Agder",
            lat=58.461,
            lon=8.772,
            property_type="Leilighet",
            ownership_type="Borettslag",
            bedrooms=2,
            energy_label="C",
            build_year=1998,
            listing_text="Lys leilighet med potensiale for ekstra rom.",
            published_at=now,
        ),
    ]
