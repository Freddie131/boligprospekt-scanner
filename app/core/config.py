from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RegionRentConfig(BaseModel):
    base_kr_per_m2: float = 160.0


class FinanceConfig(BaseModel):
    annual_interest_rate: float = 0.055
    loan_to_value: float = 0.75
    amortization_years: int = 30


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "BoligProspekt-Scanner"
    environment: str = "dev"
    ingest_mode: Literal["finn_api", "email", "mock"] = "mock"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/boligprospekt"
    redis_url: str = "redis://localhost:6379/0"

    finn_api_base_url: str = "https://api.finn.no"
    finn_api_key: str | None = None
    finn_org_id: str | None = None

    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    imap_username: str | None = None
    imap_password: str | None = None
    imap_mailbox: str = "INBOX"
    email_sender_filter: str = "varslinger@finn.no"

    max_price_nok: int = 15_000_000
    min_price_nok: int = 0
    target_regions: list[str] = Field(default_factory=lambda: ["Agder", "Telemark", "Rogaland", "Vestfold"])

    grimstad_lat: float = 58.3405
    grimstad_lon: float = 8.5934

    document_fee_rate: float = 0.025
    tinglysing_fee_per_doc: int = 545
    default_tinglysing_documents: int = 2

    maintenance_buffer_rate: float = 0.01
    municipal_fee_monthly: int = 1800
    insurance_monthly: int = 500

    region_rent_defaults: dict[str, RegionRentConfig] = Field(
        default_factory=lambda: {
            "Agder": RegionRentConfig(base_kr_per_m2=165),
            "Telemark": RegionRentConfig(base_kr_per_m2=150),
            "Rogaland": RegionRentConfig(base_kr_per_m2=190),
            "Vestfold": RegionRentConfig(base_kr_per_m2=175),
            "default": RegionRentConfig(base_kr_per_m2=155),
        }
    )
    finance: FinanceConfig = Field(default_factory=FinanceConfig)

    report_output_dir: str = "reports"


@lru_cache
def get_settings() -> Settings:
    return Settings()
