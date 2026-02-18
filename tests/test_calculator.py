from app.core.config import Settings
from app.domain.models import DataSource, Prospect
from app.services.calculator import monthly_financing_cost, purchase_cost, scenario_metrics


def make_prospect(**kwargs):
    base = dict(
        source=DataSource.mock,
        external_id="t1",
        title="Test",
        url="https://example.com",
        price_nok=2_000_000,
        ownership_type="Selveier",
        size_m2=80,
        bedrooms=2,
    )
    base.update(kwargs)
    return Prospect(**base)


def test_purchase_cost_selveier_includes_document_fee_and_tinglysing():
    settings = Settings()
    p = make_prospect(price_nok=2_000_000, ownership_type="Selveier")
    expected = 2_000_000 + 2_000_000 * settings.document_fee_rate + settings.default_tinglysing_documents * settings.tinglysing_fee_per_doc
    assert purchase_cost(p, settings) == expected


def test_purchase_cost_borettslag_no_document_fee():
    settings = Settings()
    p = make_prospect(price_nok=2_000_000, ownership_type="Borettslag")
    expected = 2_000_000 + settings.default_tinglysing_documents * settings.tinglysing_fee_per_doc
    assert purchase_cost(p, settings) == expected


def test_monthly_financing_cost_positive():
    settings = Settings()
    assert monthly_financing_cost(2_000_000, settings) > 0


def test_scenarios_return_three_variants():
    settings = Settings()
    p = make_prospect(listing_text="Oppussingsobjekt", build_year=1970)
    scenarios = scenario_metrics(p, settings)
    assert len(scenarios) == 3
    assert scenarios[1].estimated_rent_monthly >= scenarios[0].estimated_rent_monthly
