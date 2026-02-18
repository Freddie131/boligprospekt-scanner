from app.core.config import Settings
from app.domain.models import DataSource, Prospect
from app.services.scoring import calculate_score


def make_prospect(**kwargs):
    base = dict(
        source=DataSource.mock,
        external_id="s1",
        title="Test",
        url="https://example.com",
        price_nok=2_500_000,
        size_m2=90,
        bedrooms=3,
        ownership_type="Selveier",
        region="Agder",
        lat=58.34,
        lon=8.6,
    )
    base.update(kwargs)
    return Prospect(**base)


def test_score_is_bounded_0_100():
    score, _ = calculate_score(make_prospect(), Settings())
    assert 0 <= score <= 100


def test_risk_flags_reduce_score():
    settings = Settings()
    clean_score, _ = calculate_score(make_prospect(listing_text="pen bolig"), settings)
    risky_score, detail = calculate_score(make_prospect(listing_text="fukt og råte"), settings)
    assert risky_score < clean_score
    assert "fukt" in detail["risk_flags"]
