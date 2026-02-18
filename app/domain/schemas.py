from datetime import datetime

from pydantic import BaseModel, Field


class ProspectIn(BaseModel):
    source: str
    external_id: str
    title: str = "Ukjent"
    url: str
    price_nok: float | None = None
    common_costs_monthly: float | None = None
    size_m2: float | None = None
    lot_m2: float | None = None
    address: str | None = None
    municipality: str | None = None
    region: str | None = None
    lat: float | None = None
    lon: float | None = None
    property_type: str | None = None
    ownership_type: str | None = None
    bedrooms: int | None = None
    energy_label: str | None = None
    build_year: int | None = None
    listing_text: str | None = None
    published_at: datetime | None = None


class ProspectOverrideUpdate(BaseModel):
    manual_rent_override: float | None = None
    manual_renovation_override: float | None = None
    manual_extra_bedroom_possible: bool | None = None


class ProspectOut(BaseModel):
    id: int
    title: str
    url: str
    price_nok: float | None
    region: str | None
    municipality: str | None
    score: float | None
    status: str
    metrics: dict = Field(default_factory=dict)

    class Config:
        from_attributes = True
