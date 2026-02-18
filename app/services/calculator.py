from dataclasses import dataclass

from app.core.config import Settings
from app.domain.models import Prospect


@dataclass
class ScenarioResult:
    scenario: str
    estimated_rent_monthly: float
    monthly_costs: float
    net_cashflow_monthly: float
    cap_rate: float
    cash_on_cash: float
    renovation_payback_years: float | None


RISK_KEYWORDS = [
    "fukt",
    "råte",
    "drenering",
    "skadedyr",
    "asbest",
    "totalrenoveres",
    "moderniseringsbehov",
]


def purchase_cost(prospect: Prospect, settings: Settings) -> float:
    price = prospect.price_nok or 0
    docs = settings.default_tinglysing_documents * settings.tinglysing_fee_per_doc
    if (prospect.ownership_type or "").lower() in {"borettslag", "andel"}:
        return price + docs
    return price + price * settings.document_fee_rate + docs


def monthly_financing_cost(principal: float, settings: Settings) -> float:
    loan = principal * settings.finance.loan_to_value
    r = settings.finance.annual_interest_rate / 12
    n = settings.finance.amortization_years * 12
    if loan <= 0:
        return 0
    return loan * (r * (1 + r) ** n) / ((1 + r) ** n - 1)


def estimate_rent_monthly(prospect: Prospect, settings: Settings, bedrooms_delta: int = 0, light_upgrade=False) -> float:
    if prospect.manual_rent_override:
        base = prospect.manual_rent_override
    else:
        region = prospect.region or "default"
        base_rate = settings.region_rent_defaults.get(region, settings.region_rent_defaults["default"]).base_kr_per_m2
        base = (prospect.size_m2 or 40) * base_rate
    if prospect.energy_label in {"A", "B"}:
        base *= 1.05
    if light_upgrade:
        base *= 1.08
    if bedrooms_delta > 0:
        base += bedrooms_delta * 1500
    return base / 12


def estimate_renovation_cost(prospect: Prospect) -> float:
    if prospect.manual_renovation_override is not None:
        return prospect.manual_renovation_override
    text = (prospect.listing_text or "").lower()
    base = 0.0
    if any(k in text for k in ["oppussingsobjekt", "moderniseringsbehov", "totalrenoveres"]):
        base += 350_000
    if prospect.build_year and prospect.build_year < 1980:
        base += 180_000
    return base


def can_add_bedroom(prospect: Prospect) -> bool:
    if prospect.manual_extra_bedroom_possible is not None:
        return prospect.manual_extra_bedroom_possible
    if not prospect.size_m2:
        return False
    bedrooms = prospect.bedrooms or 1
    return prospect.size_m2 / bedrooms > 35


def detect_risk_flags(prospect: Prospect) -> list[str]:
    text = (prospect.listing_text or "").lower()
    return [k for k in RISK_KEYWORDS if k in text]


def scenario_metrics(prospect: Prospect, settings: Settings) -> list[ScenarioResult]:
    total_purchase = purchase_cost(prospect, settings)
    base_fin = monthly_financing_cost(total_purchase, settings)
    common = prospect.common_costs_monthly or 0
    maintenance = (prospect.price_nok or 0) * settings.maintenance_buffer_rate / 12
    fixed = settings.municipal_fee_monthly + settings.insurance_monthly + common + maintenance + base_fin

    reno = estimate_renovation_cost(prospect)
    s0_rent = estimate_rent_monthly(prospect, settings)
    s1_rent = estimate_rent_monthly(prospect, settings, light_upgrade=True)
    extra = 1 if can_add_bedroom(prospect) else 0
    s2_rent = estimate_rent_monthly(prospect, settings, bedrooms_delta=extra, light_upgrade=True)

    def build(scenario: str, rent: float, reno_cost: float) -> ScenarioResult:
        net = rent - fixed
        annual_net = net * 12
        cap = annual_net / max(total_purchase + reno_cost, 1)
        equity = (total_purchase + reno_cost) * (1 - settings.finance.loan_to_value)
        coc = annual_net / max(equity, 1)
        payback = (reno_cost / max((rent - s0_rent) * 12, 1)) if reno_cost > 0 and rent > s0_rent else None
        return ScenarioResult(scenario, round(rent, 2), round(fixed, 2), round(net, 2), round(cap, 4), round(coc, 4), round(payback, 2) if payback else None)

    return [
        build("S0_as_is", s0_rent, 0),
        build("S1_light_reno", s1_rent, reno),
        build("S2_reno_plus_bedroom", s2_rent, reno + (120_000 if extra else 0)),
    ]
