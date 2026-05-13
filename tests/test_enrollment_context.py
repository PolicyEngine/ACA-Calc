"""Tests for CMS Marketplace enrollment context helpers."""

from aca_calc.enrollment_context import get_enrollment_context


def test_healthcare_gov_county_with_compact_data_returns_context():
    context = get_enrollment_context("TX", "Travis County")

    assert context.status == "county_context_available"
    assert context.marketplace_platform == "HealthCare.gov"
    assert context.fine_grained_cms_available
    assert context.county_context_available
    assert context.marketplace_plan_selections == 184_355
    assert context.aptc_consumers == 162_349
    assert context.average_aptc == 562


def test_state_based_marketplace_state_returns_fallback_status():
    context = get_enrollment_context("CA", "San Benito County")

    assert context.status == "state_based_marketplace_fallback"
    assert context.marketplace_platform == "State-based marketplace"
    assert not context.fine_grained_cms_available
    assert not context.county_context_available
    assert context.marketplace_plan_selections is None
    assert "falls back to state-level context" in context.message


def test_unknown_county_in_healthcare_gov_state_is_graceful():
    context = get_enrollment_context("TX", "Not A County")

    assert context.status == "not_in_compact_dataset"
    assert context.marketplace_platform == "HealthCare.gov"
    assert context.fine_grained_cms_available
    assert not context.county_context_available
    assert context.marketplace_plan_selections is None


def test_second_healthcare_gov_county_from_compact_data_returns_context():
    context = get_enrollment_context("OR", "Multnomah County")

    assert context.status == "county_context_available"
    assert context.marketplace_plan_selections == 28_221
    assert context.aptc_consumers == 15_466


def test_display_county_name_can_match_official_census_county_name():
    context = get_enrollment_context("AK", "Haines")

    assert context.status == "county_context_available"
    assert context.county == "Haines Borough"


def test_unknown_state_is_graceful():
    context = get_enrollment_context("ZZ", "Example County")

    assert context.status == "unknown_state"
    assert context.marketplace_platform == "Unknown"
    assert not context.fine_grained_cms_available
    assert not context.county_context_available
