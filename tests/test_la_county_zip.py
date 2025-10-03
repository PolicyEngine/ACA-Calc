"""
Test Los Angeles County zip code requirement

LA County has multiple rating areas based on zip code, so PolicyEngine
requires a zip code to determine the SLCSP rating area.
"""

import pytest
from policyengine_us import Simulation


def test_la_county_requires_zip_code():
    """LA County should work with a valid zip code"""
    situation = {
        "people": {
            "you": {"age": {2026: 30}, "employment_income": {2026: 50000}}
        },
        "families": {"your family": {"members": ["you"]}},
        "spm_units": {"your household": {"members": ["you"]}},
        "tax_units": {"your tax unit": {"members": ["you"]}},
        "households": {
            "your household": {
                "members": ["you"],
                "state_name": {2026: "CA"},
                "county": {2026: "LOS_ANGELES_COUNTY_CA"},
                "zip_code": {2026: "90001"},  # South LA zip code
            }
        },
    }

    sim = Simulation(situation=situation)

    # Should be able to calculate SLCSP without error
    slcsp = sim.calculate("slcsp", map_to="household", period=2026)[0]
    assert slcsp > 0, "SLCSP should be calculated for LA County with zip code"

    # Should also calculate PTC
    ptc = sim.calculate("aca_ptc", map_to="household", period=2026)[0]
    # PTC may or may not be positive depending on SLCSP and income, but should not error
    assert ptc >= 0


def test_la_county_different_zip_codes():
    """Different LA County zip codes should potentially have different SLCSPs"""
    # Downtown LA
    situation_downtown = {
        "people": {
            "you": {"age": {2026: 30}, "employment_income": {2026: 40000}}
        },
        "families": {"your family": {"members": ["you"]}},
        "spm_units": {"your household": {"members": ["you"]}},
        "tax_units": {"your tax unit": {"members": ["you"]}},
        "households": {
            "your household": {
                "members": ["you"],
                "state_name": {2026: "CA"},
                "county": {2026: "LOS_ANGELES_COUNTY_CA"},
                "zip_code": {2026: "90012"},  # Downtown LA
            }
        },
    }

    # Santa Monica
    situation_santa_monica = {
        "people": {
            "you": {"age": {2026: 30}, "employment_income": {2026: 40000}}
        },
        "families": {"your family": {"members": ["you"]}},
        "spm_units": {"your household": {"members": ["you"]}},
        "tax_units": {"your tax unit": {"members": ["you"]}},
        "households": {
            "your household": {
                "members": ["you"],
                "state_name": {2026: "CA"},
                "county": {2026: "LOS_ANGELES_COUNTY_CA"},
                "zip_code": {2026: "90401"},  # Santa Monica
            }
        },
    }

    sim1 = Simulation(situation=situation_downtown)
    sim2 = Simulation(situation=situation_santa_monica)

    slcsp1 = sim1.calculate("slcsp", map_to="household", period=2026)[0]
    slcsp2 = sim2.calculate("slcsp", map_to="household", period=2026)[0]

    # Both should calculate successfully
    assert slcsp1 > 0
    assert slcsp2 > 0

    # They might be different (depending on rating areas) but at least they should both work
    # Note: We're not asserting they're different because they might be in the same rating area


def test_other_california_counties_work_without_zip():
    """Other CA counties should work without zip code"""
    situation = {
        "people": {
            "you": {"age": {2026: 30}, "employment_income": {2026: 50000}}
        },
        "families": {"your family": {"members": ["you"]}},
        "spm_units": {"your household": {"members": ["you"]}},
        "tax_units": {"your tax unit": {"members": ["you"]}},
        "households": {
            "your household": {
                "members": ["you"],
                "state_name": {2026: "CA"},
                "county": {2026: "ALAMEDA_COUNTY_CA"},
                # No zip code - should work fine for non-LA counties
            }
        },
    }

    sim = Simulation(situation=situation)
    slcsp = sim.calculate("slcsp", map_to="household", period=2026)[0]
    assert slcsp > 0, "Non-LA CA counties should work without zip code"
