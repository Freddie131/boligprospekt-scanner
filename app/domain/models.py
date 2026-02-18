from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Boolean, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ProspectStatus(str, Enum):
    active = "active"
    needs_manual_enrichment = "needs_manual_enrichment"
    archived = "archived"


class DataSource(str, Enum):
    finn_api = "finn_api"
    email = "email"
    mock = "mock"


class Prospect(Base):
    __tablename__ = "prospects"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_source_external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[DataSource] = mapped_column(SQLEnum(DataSource), nullable=False)
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(300), default="Ukjent")
    url: Mapped[str] = mapped_column(String(1000))

    price_nok: Mapped[float | None] = mapped_column(Float)
    common_costs_monthly: Mapped[float | None] = mapped_column(Float)
    size_m2: Mapped[float | None] = mapped_column(Float)
    lot_m2: Mapped[float | None] = mapped_column(Float)
    address: Mapped[str | None] = mapped_column(String(300))
    municipality: Mapped[str | None] = mapped_column(String(120))
    region: Mapped[str | None] = mapped_column(String(120))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    property_type: Mapped[str | None] = mapped_column(String(120))
    ownership_type: Mapped[str | None] = mapped_column(String(120))
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    energy_label: Mapped[str | None] = mapped_column(String(20))
    build_year: Mapped[int | None] = mapped_column(Integer)
    listing_text: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped[ProspectStatus] = mapped_column(SQLEnum(ProspectStatus), default=ProspectStatus.active)
    manual_rent_override: Mapped[float | None] = mapped_column(Float)
    manual_renovation_override: Mapped[float | None] = mapped_column(Float)
    manual_extra_bedroom_possible: Mapped[bool | None] = mapped_column(Boolean)

    risk_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    score: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    price_history: Mapped[list["PriceHistory"]] = relationship(back_populates="prospect", cascade="all, delete-orphan")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    price_nok: Mapped[float] = mapped_column(Float, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    prospect: Mapped[Prospect] = relationship(back_populates="price_history")


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_name: Mapped[str] = mapped_column(String(120), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), default="running")
    records_ingested: Mapped[int] = mapped_column(Integer, default=0)
    report_html_path: Mapped[str | None] = mapped_column(String(500))
    report_pdf_path: Mapped[str | None] = mapped_column(String(500))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
