"""The calculator API at one level of earnings, which the calculator's "Your
household" tab shows, and the income axis at exactly 400% FPL.

The households and incomes are the ones the agent review of November 20 found
the tab got wrong when it read between the axis's $1,000 steps.
"""

import pytest

TestClient = pytest.importorskip(
    "fastapi.testclient",
    reason="API tests require FastAPI: run uv run --with fastapi pytest",
).TestClient

from src.aca_api import api

PENNSYLVANIA = {"age_head": 45, "state": "PA", "county": "Lebanon County"}
TEXAS = {"age_head": 40, "state": "TX", "county": "Harris County"}
FLORIDA = {
    "age_head": 40,
    "age_spouse": 40,
    "dependent_ages": [10, 8],
    "state": "FL",
    "county": "Hillsborough County",
}
ANCHORAGE = {
    "age_head": 45,
    "age_spouse": 43,
    "dependent_ages": [8],
    "state": "AK",
    "county": "Anchorage Municipality",
}
# What the calculator page asks for.
PAGE = {"year": 2027, "show_ira": True, "show_prior_year": True, "skip_cache": True}


@pytest.fixture(scope="module")
def client():
    with TestClient(api.app) as client:
        yield client


def at_income(client, household, income):
    response = client.post("/api/calculate-at-income", json={**household, **PAGE, "income": income})
    assert response.status_code == 200, response.text
    return response.json()


def monthly(scenario, field="credit"):
    return scenario[field] / 12


def test_the_answer_names_the_household_and_each_scenario(client):
    answer = at_income(client, FLORIDA, 75_000)
    assert answer["year"] == 2027
    assert answer["income"] == 75_000
    assert answer["model_version"] == api.MODEL_VERSION
    assert [p["relationship"] for p in answer["people"]] == ["head", "spouse", "dependent", "dependent"]
    assert [p["age"] for p in answer["people"]] == [40, 40, 10, 8]
    assert answer["current"]["year"] == 2027 and answer["ira"]["year"] == 2027
    assert answer["prior_year"]["year"] == 2026
    # 2027 credits use the 2026 guideline; 2026 credits the 2025 one.
    assert answer["current"]["fpl"] == 33_000
    assert answer["prior_year"]["fpl"] == 32_150


def test_just_above_medicaid_the_credit_is_the_one_at_that_income(client):
    # 143% FPL in 2026, above Medicaid's 138%: the card showed no credit, the
    # closest $1,000 step's.
    prior = at_income(client, PENNSYLVANIA, 22_400)["prior_year"]
    assert not prior["coverage"][0]["medicaid"]
    assert monthly(prior) == pytest.approx(1_056.7, abs=0.5)


def test_just_below_133_percent_the_credit_uses_that_incomes_share(client):
    # The share of income jumps at 133% FPL; the card blended the two sides.
    current = at_income(client, FLORIDA, 43_889.99)["current"]
    assert monthly(current) == pytest.approx(1_297.94, abs=0.01)


def test_the_children_alone_are_on_medicaid(client):
    current = at_income(client, FLORIDA, 40_000)["current"]
    assert [p["medicaid"] for p in current["coverage"]] == [False, False, True, True]
    assert monthly(current) == pytest.approx(1_304.91, abs=0.01)


def test_exactly_400_percent_qualifies_and_a_dollar_more_does_not(client):
    # 26 U.S.C. 36B(c)(1)(A): income that "does not exceed 400 percent".
    assert monthly(at_income(client, FLORIDA, 132_000)["current"]) == pytest.approx(1_076.37, abs=0.01)
    assert at_income(client, FLORIDA, 132_001)["current"]["credit"] == 0
    assert at_income(client, FLORIDA, 132_200)["current"]["credit"] == 0


def test_the_income_axis_pays_the_credit_at_exactly_400_percent(client):
    response = client.post("/api/calculate", json={**FLORIDA, **PAGE})
    assert response.status_code == 200, response.text
    answer = response.json()
    at_limit = answer["income"].index(132_000)
    assert answer["ptc_baseline"][at_limit] / 12 == pytest.approx(1_076.37, abs=0.01)
    assert answer["ptc_baseline"][at_limit + 1] == 0
    # 2026's 400% FPL, $128,600, isn't on the axis.
    assert answer["magi"] == answer["income"]


def test_hr1834s_credit_ends_where_85_percent_of_income_reaches_the_benchmark(client):
    assert at_income(client, PENNSYLVANIA, 174_550)["ira"]["credit"] == 0
    assert at_income(client, PENNSYLVANIA, 174_000)["ira"]["credit"] > 0


def test_alaskas_dividend_counts_toward_the_credits_income(client):
    # $134,550 of earnings and two $1,000 dividends: 399.9% FPL.
    current = at_income(client, ANCHORAGE, 134_550)["current"]
    assert current["magi"] == 136_550
    assert current["fpl"] == 34_150
    assert monthly(current) == pytest.approx(2_463.70, abs=0.01)


def test_in_the_coverage_gap_a_plan_costs_its_full_premium(client):
    # Texas didn't expand Medicaid; at 97% FPL there's no credit, and the model
    # prices no plan.
    current = at_income(client, TEXAS, 15_500)["current"]
    assert current["benchmark"] == 0 and current["credit"] == 0
    assert monthly(current, "full_premium") == pytest.approx(770.15, abs=0.01)
    assert current["coverage"] == [{"medicaid": False, "chip": False, "medicaid_work_requirement": False}]


def test_the_full_premium_is_the_benchmark_where_the_model_prices_one(client):
    current = at_income(client, TEXAS, 40_000)["current"]
    assert current["full_premium"] == current["benchmark"] > 0


def test_from_2027_medicaids_work_requirement_bars_low_earnings(client):
    # Pennsylvania expanded Medicaid, but $5,000 is under 80 hours a month at
    # the federal minimum wage.
    answer = at_income(client, PENNSYLVANIA, 5_000)
    assert answer["current"]["coverage"][0] == {
        "medicaid": False,
        "chip": False,
        "medicaid_work_requirement": True,
    }
    assert answer["prior_year"]["coverage"][0]["medicaid"]


def test_the_answer_matches_the_income_axis_at_a_calculated_income(client):
    axis = client.post("/api/calculate", json={**TEXAS, **PAGE}).json()
    i = axis["income"].index(40_000)
    answer = at_income(client, TEXAS, 40_000)
    assert answer["current"]["credit"] == pytest.approx(axis["ptc_baseline"][i], abs=0.01)
    assert answer["ira"]["credit"] == pytest.approx(axis["ptc_ira"][i], abs=0.01)
    assert answer["prior_year"]["credit"] == pytest.approx(axis["ptc_prior_year"][i], abs=0.01)
    assert answer["current"]["benchmark"] == pytest.approx(axis["slcsp_by_income"][i], abs=0.01)


@pytest.mark.parametrize("income", [-1, 1_000_001])
def test_earnings_outside_0_to_1_million_are_refused(client, income):
    response = client.post("/api/calculate-at-income", json={**TEXAS, **PAGE, "income": income})
    assert response.status_code == 422


def test_the_cache_key_names_the_income(monkeypatch):
    from src.aca_api.models import AtIncomeRequest, CalculateRequest

    key = lambda income: api.get_cache_key(AtIncomeRequest(**TEXAS, income=income))
    assert key(40_000) != key(41_000)
    assert key(40_000) != api.get_cache_key(CalculateRequest(**TEXAS))
