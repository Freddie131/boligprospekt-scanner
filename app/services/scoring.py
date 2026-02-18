from app.core.config import Settings
from app.domain.models import Prospect
from app.services.calculator import detect_risk_flags, scenario_metrics
from app.services.geo import haversine_km


def calculate_score(prospect: Prospect, settings: Settings) -> tuple[float, dict]:
    metrics = scenario_metrics(prospect, settings)
    best = max(metrics, key=lambda m: m.net_cashflow_monthly)

    proximity = _proximity_score(prospect, settings)
    cashflow_component = min(max(best.net_cashflow_monthly / 5000, -1), 1) * 25 + 25
    value_add = 20
    if metrics[-1].estimated_rent_monthly > metrics[0].estimated_rent_monthly:
        value_add += 10
    if prospect.price_nok and prospect.size_m2 and prospect.price_nok / prospect.size_m2 < 35000:
        value_add += 10

    risk_flags = detect_risk_flags(prospect)
    risk_penalty = min(len(risk_flags) * 8, 25)

    data_quality_penalty = 0
    for required in [prospect.price_nok, prospect.size_m2, prospect.bedrooms]:
        if required in (None, 0):
            data_quality_penalty += 5

    score = max(min(proximity + cashflow_component + value_add - risk_penalty - data_quality_penalty, 100), 0)
    detail = {
        "proximity": proximity,
        "cashflow": cashflow_component,
        "value_add": value_add,
        "risk_penalty": risk_penalty,
        "data_quality_penalty": data_quality_penalty,
        "risk_flags": risk_flags,
        "scenarios": [m.__dict__ for m in metrics],
    }
    return round(score, 2), detail


def _proximity_score(prospect: Prospect, settings: Settings) -> float:
    if prospect.lat is None or prospect.lon is None:
        return 18
    distance = haversine_km(settings.grimstad_lat, settings.grimstad_lon, prospect.lat, prospect.lon)
    if distance <= 20:
        return 40
    if distance <= 60:
        return 34
    if distance <= 120:
        return 26
    if distance <= 200:
        return 18
    return 10
