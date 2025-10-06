"""Tests for household situation building."""

import pytest
from aca_calc.calculations.household import build_household_situation


def test_single_person():
    """Test single person household."""
    situation = build_household_situation(
        age_head=35,
        age_spouse=None,
        dependent_ages=[],
        state="CA",
    )

    assert "you" in situation["people"]
    assert situation["people"]["you"]["age"] == {2026: 35}
    assert len(situation["households"]["your household"]["members"]) == 1
    assert "marital_units" not in situation


def test_married_couple():
    """Test married couple household."""
    situation = build_household_situation(
        age_head=35,
        age_spouse=33,
        dependent_ages=[],
        state="CA",
    )

    assert "you" in situation["people"]
    assert "your partner" in situation["people"]
    assert len(situation["households"]["your household"]["members"]) == 2
    assert "marital_units" in situation
    assert "your marital unit" in situation["marital_units"]


def test_with_dependents():
    """Test household with children."""
    situation = build_household_situation(
        age_head=35,
        age_spouse=None,
        dependent_ages=[10, 8, 5],
        state="CA",
    )

    assert "you" in situation["people"]
    assert "your first dependent" in situation["people"]
    assert "your second dependent" in situation["people"]
    assert "dependent_3" in situation["people"]
    assert len(situation["households"]["your household"]["members"]) == 4


def test_with_county():
    """Test household with county specified."""
    situation = build_household_situation(
        age_head=35,
        age_spouse=None,
        dependent_ages=[],
        state="TX",
        county="Travis County",
    )

    assert situation["households"]["your household"]["county"] == {
        2026: "TRAVIS_COUNTY_TX"
    }


def test_with_zip_code():
    """Test household with ZIP code (LA County)."""
    situation = build_household_situation(
        age_head=35,
        age_spouse=None,
        dependent_ages=[],
        state="CA",
        county="Los Angeles County",
        zip_code="90001",
    )

    assert situation["households"]["your household"]["zip_code"] == {2026: "90001"}


def test_with_axes():
    """Test household with income axes for sweeps."""
    situation = build_household_situation(
        age_head=35,
        age_spouse=None,
        dependent_ages=[],
        state="CA",
        with_axes=True,
    )

    assert "axes" in situation
    assert situation["axes"][0][0]["name"] == "employment_income"
    assert situation["axes"][0][0]["count"] == 10_001
