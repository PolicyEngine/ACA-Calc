"""The calculator API for 2026 and 2027 coverage, and its extension scenarios.

A single 60-year-old in Travis County, Texas: Texas didn't expand Medicaid, so
the credit starts at 100% FPL, and at 60 the benchmark premium is above 8.5%
of income well past 400% FPL, so the scenarios' differences there show.
"""

import numpy as np
import pytest
from policyengine_us import Simulation
from pydantic import ValidationError

TestClient = pytest.importorskip(
    "fastapi.testclient",
    reason="API tests require FastAPI: run uv run --with fastapi pytest",
).TestClient

from aca_calc.calculations.household import build_household_situation
from aca_calc.calculations.reforms import minimum_premium_available
from src.aca_api import api
from src.aca_api.models import CalculateRequest

HOUSEHOLD = {"age_head": 60, "state": "TX", "county": "Travis County", "skip_cache": True}
ALL_SCENARIOS = {
    "show_ira": True,
    "show_700fpl": True,
    "show_additional_bracket": True,
    "show_simplified_bracket": True,
    "show_700fpl_cap": True,
    "show_min_premium": True,
}
# Single-person poverty guidelines for the 48 states and Alaska (HHS).
GUIDELINE_2025 = 15_650
GUIDELINE_2026 = 15_960
ALASKA_GUIDELINE_2026 = 19_950


@pytest.fixture(scope="module")
def client():
    with TestClient(api.app) as client:
        yield client


@pytest.fixture(scope="module")
def answer_2027(client):
    """Current law and every available scenario for 2027 coverage."""
    response = client.post("/api/calculate", json={**HOUSEHOLD, **ALL_SCENARIOS, "year": 2027})
    assert response.status_code == 200, response.text
    answer = {
        key: np.array(value) if isinstance(value, list) else value
        for key, value in response.json().items()
    }
    # Income as a multiple of the guideline the credit uses. Points within 1%
    # of a limit are left out of the checks, since the credit's FPL fraction is
    # truncated to whole percents.
    answer["multiple"] = answer["income"] / answer["fpl"]
    return answer


def between(answer, low, high):
    multiple = answer["multiple"]
    return (multiple > low * 1.01) & (multiple < high * 0.99)


def test_requests_without_a_year_get_2026():
    assert CalculateRequest(age_head=40, state="TX", county="Travis County").year == 2026


@pytest.mark.parametrize("year", [2025, 2028])
def test_other_years_are_refused(year):
    with pytest.raises(ValidationError, match="year must be one of 2026, 2027"):
        CalculateRequest(age_head=40, state="TX", county="Travis County", year=year)


def test_the_cache_key_names_the_year_and_the_model_version(monkeypatch):
    request = {"age_head": 40, "state": "TX", "county": "Travis County"}
    key_2026 = api.get_cache_key(CalculateRequest(**request, year=2026))
    key_2027 = api.get_cache_key(CalculateRequest(**request, year=2027))
    assert key_2026 != key_2027
    monkeypatch.setattr(api, "MODEL_VERSION", "another version")
    assert api.get_cache_key(CalculateRequest(**request, year=2026)) != key_2026


def test_the_answer_names_its_year_guideline_and_model(answer_2027):
    assert answer_2027["year"] == 2027
    # 2027 credits measure income against the 2026 guideline.
    assert answer_2027["fpl_year"] == 2026
    assert answer_2027["fpl"] == GUIDELINE_2026
    assert answer_2027["model_version"] == api.MODEL_VERSION


def test_alaska_households_get_alaskas_prior_year_guideline():
    situation = build_household_situation(40, None, [], "AK", county="Anchorage Municipality", year=2027)
    sim = Simulation(situation=situation)
    assert float(sim.calculate("tax_unit_fpg", 2026)[0]) == ALASKA_GUIDELINE_2026


def test_current_law_in_2027_ends_the_credit_at_400_percent(answer_2027):
    baseline = answer_2027["ptc_baseline"]
    assert (baseline[between(answer_2027, 1.5, 4)] > 0).all()
    assert (baseline[answer_2027["multiple"] > 4.01] == 0).all()


def test_hr1834_in_2027_charges_nothing_below_150_percent(answer_2027):
    # The enhanced schedule's required contribution is 0% of income there, so
    # the credit is the whole benchmark premium.
    below_150 = between(answer_2027, 1, 1.5)
    assert below_150.any()
    np.testing.assert_allclose(answer_2027["ptc_ira"][below_150], answer_2027["slcsp"], atol=1)


def test_hr1834_in_2027_continues_above_400_percent(answer_2027):
    assert (answer_2027["ptc_ira"][between(answer_2027, 4, 7)] > 0).all()


def test_the_700_percent_cap_follows_hr1834_and_ends_at_700_percent(answer_2027):
    below_700 = between(answer_2027, 1, 7)
    np.testing.assert_allclose(
        answer_2027["ptc_700fpl_cap"][below_700], answer_2027["ptc_ira"][below_700], atol=1
    )
    above_700 = answer_2027["multiple"] > 7.01
    assert (answer_2027["ptc_700fpl_cap"][above_700] == 0).all()
    assert (answer_2027["ptc_ira"][above_700 & (answer_2027["multiple"] < 8)] > 0).all()


@pytest.mark.parametrize(
    "field", ["ptc_700fpl", "ptc_additional_bracket", "ptc_simplified_bracket"]
)
def test_the_other_scenarios_run_for_2027(answer_2027, field):
    values = answer_2027[field]
    assert len(values) == len(answer_2027["income"])
    assert values[between(answer_2027, 1.5, 4)].max() > 0


def test_a_scenario_that_is_off_returns_zeros(client):
    response = client.post("/api/calculate", json={**HOUSEHOLD, "show_ira": True})
    assert response.status_code == 200, response.text
    answer = response.json()
    assert answer["year"] == 2026
    assert answer["fpl"] == GUIDELINE_2025
    assert max(answer["ptc_ira"]) > 0
    for field in ("ptc_700fpl", "ptc_700fpl_cap", "ptc_min_premium"):
        assert len(answer[field]) == len(answer["income"])
        assert max(answer[field]) == 0


def test_the_installed_model_has_the_minimum_premium():
    assert minimum_premium_available()


def test_the_minimum_premium_leaves_60_dollars_where_hr1834_covers_the_premium(answer_2027):
    # Below 150% FPL the enhanced schedule's contribution is 0%, so H.R. 1834's
    # credit is the whole benchmark premium; the minimum leaves $5 a month.
    below_150 = between(answer_2027, 1, 1.5)
    np.testing.assert_allclose(
        answer_2027["ptc_min_premium"][below_150], answer_2027["slcsp"] - 60, atol=1
    )


def test_the_minimum_premium_matches_hr1834_where_the_household_pays_more(answer_2027):
    # From 200% FPL the required contribution is at least 2% of income, far
    # more than $60 a year, so the minimum doesn't bind.
    above_200 = between(answer_2027, 2, 7)
    np.testing.assert_allclose(
        answer_2027["ptc_min_premium"][above_200], answer_2027["ptc_ira"][above_200], atol=1
    )


def test_a_model_without_the_minimum_premium_says_what_it_needs(client, monkeypatch):
    monkeypatch.setattr(api, "minimum_premium_available", lambda: False)
    request = {**HOUSEHOLD, "show_ira": False, "show_min_premium": True, "year": 2027}
    response = client.post("/api/calculate", json=request)
    assert response.status_code == 400
    assert "gov.contrib.aca.minimum_premium" in response.json()["detail"]
    stream = client.post("/api/calculate-stream", json=request)
    assert '"step": "error"' in stream.text
    assert "gov.contrib.aca.minimum_premium" in stream.text
