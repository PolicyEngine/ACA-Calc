"""
Test that income increments in chart are exact 1k intervals
"""
import pytest
from policyengine_us import Simulation
import numpy as np


def test_understand_axes_behavior():
    """Understand how PolicyEngine axes work"""
    # Test with small count to understand pattern
    situation = {
        "people": {"you": {"age": {2026: 35}}},
        "families": {"your family": {"members": ["you"]}},
        "spm_units": {"your household": {"members": ["you"]}},
        "tax_units": {"your tax unit": {"members": ["you"]}},
        "households": {
            "your household": {
                "members": ["you"],
                "state_name": {2026: "TX"}
            }
        },
        "axes": [
            [
                {
                    "name": "employment_income",
                    "count": 11,  # Should give us 0, 10k, 20k, ..., 100k if using 10k steps
                    "min": 0,
                    "max": 100000
                }
            ]
        ]
    }

    sim = Simulation(situation=situation)
    income_range = sim.calculate("employment_income", map_to="household", period=2026)

    print(f"\nWith count=11, min=0, max=100000:")
    print(f"Got {len(income_range)} values")
    print(f"Values: {income_range}")
    print(f"First value: {income_range[0]}")
    print(f"Last value: {income_range[-1]}")

    # Check if it's exponential/logarithmic
    import numpy as np
    print(f"\nExpected linspace: {np.linspace(0, 100000, 11)}")
    print(f"\nExpected logspace (excluding 0): {np.logspace(0, 5, 11)}")


def test_axes_with_adjusted_max():
    """Test with adjusted max to account for PolicyEngine's overshoot"""
    # PolicyEngine overshoots by ratio of ~1.09689
    # To get max of 1,000,000, use: 1,000,000 / 1.09689 = 911,570
    adjusted_max = round(1000000 / 1.09689)

    situation = {
        "people": {"you": {"age": {2026: 35}}},
        "families": {"your family": {"members": ["you"]}},
        "spm_units": {"your household": {"members": ["you"]}},
        "tax_units": {"your tax unit": {"members": ["you"]}},
        "households": {
            "your household": {
                "members": ["you"],
                "state_name": {2026: "TX"}
            }
        },
        "axes": [
            [
                {
                    "name": "employment_income",
                    "count": 1001,
                    "min": 0,
                    "max": adjusted_max
                }
            ]
        ]
    }

    sim = Simulation(situation=situation)
    income_range = sim.calculate("employment_income", map_to="household", period=2026)

    print(f"\nWith count=1001, min=0, max={adjusted_max} (adjusted):")
    print(f"First 10 values: {income_range[:10]}")
    print(f"Last 10 values: {income_range[-10:]}")
    print(f"Actual last value: {income_range[-1]}")

    # Check if values are close to exact thousands
    import numpy as np
    errors = []
    for i in range(len(income_range)):
        expected = i * 1000
        actual = income_range[i]
        error = abs(actual - expected)
        if error > 1:  # More than $1 error
            errors.append((i, expected, actual, error))

    if errors:
        print(f"\nFound {len(errors)} values with >$1 error:")
        for i, exp, act, err in errors[:10]:
            print(f"  Index {i}: expected ${exp:,.0f}, got ${act:,.2f}, error ${err:,.2f}")


def test_axes_generates_exact_1k_increments():
    """Test using numpy arange directly to create exact 1k increments

    Since PolicyEngine axes don't generate exact increments, we may need
    to manually construct the income array or find the right "step" parameter.
    """
    # First, let's verify that numpy arange/linspace can do what we want
    import numpy as np
    expected_incomes = np.arange(0, 1000001, 1000)  # 0, 1000, 2000, ..., 1000000

    print(f"\nNumPy arange(0, 1000001, 1000):")
    print(f"Length: {len(expected_incomes)}")
    print(f"First 10: {expected_incomes[:10]}")
    print(f"Last 10: {expected_incomes[-10:]}")
    print(f"All are exact multiples of 1000: {all(x % 1000 == 0 for x in expected_incomes)}")

    # Check if axes supports "step" parameter
    try:
        situation = {
            "people": {"you": {"age": {2026: 35}}},
            "families": {"your family": {"members": ["you"]}},
            "spm_units": {"your household": {"members": ["you"]}},
            "tax_units": {"your tax unit": {"members": ["you"]}},
            "households": {
                "your household": {
                    "members": ["you"],
                    "state_name": {2026: "TX"}
                }
            },
            "axes": [
                [
                    {
                        "name": "employment_income",
                        "min": 0,
                        "max": 1000000,
                        "step": 1000  # Try step parameter
                    }
                ]
            ]
        }

        sim = Simulation(situation=situation)
        income_range = sim.calculate("employment_income", map_to="household", period=2026)

        print(f"\nWith step=1000 parameter:")
        print(f"Length: {len(income_range)}")
        print(f"First 10: {income_range[:10]}")
        print(f"Last 10: {income_range[-10:]}")

        # Check if all values are exact multiples of 1000
        all_exact = all(abs(x - round(x / 1000) * 1000) < 0.01 for x in income_range)
        print(f"All are exact multiples of 1000: {all_exact}")

    except Exception as e:
        print(f"\nStep parameter not supported: {e}")


def test_get_uprating_factor():
    """Find the uprating factor for employment_income in 2026"""
    from policyengine_us import Simulation

    # Create simulation and get the uprating parameter
    sim = Simulation(situation={
        "people": {"you": {}},
        "households": {"your household": {"members": ["you"]}}
    })

    # Get the uprating factor
    try:
        uprating_param = sim.tax_benefit_system.parameters.calibration.gov.irs.soi.employment_income
        uprating_2026 = uprating_param("2026-01-01")
        print(f"\nUprating factor for 2026: {uprating_2026}")
        print(f"To get actual max of 1M, use specified max of: {1000000 / uprating_2026:,.0f}")
        return uprating_2026
    except Exception as e:
        print(f"\nCouldn't get uprating factor: {e}")
        # Calculate it empirically
        situation = {
            "people": {"you": {"age": {2026: 35}}},
            "families": {"your family": {"members": ["you"]}},
            "spm_units": {"your household": {"members": ["you"]}},
            "tax_units": {"your tax unit": {"members": ["you"]}},
            "households": {
                "your household": {
                    "members": ["you"],
                    "state_name": {2026: "TX"}
                }
            },
            "axes": [
                [
                    {
                        "name": "employment_income",
                        "count": 2,
                        "min": 0,
                        "max": 100000
                    }
                ]
            ]
        }

        sim = Simulation(situation=situation)
        income = sim.calculate("employment_income", map_to="household", period=2026)
        uprating = income[-1] / 100000
        print(f"\nEmpirical uprating factor: {uprating}")
        print(f"To get actual max of 1M, use specified max of: {1000000 / uprating:,.0f}")
        return uprating


def test_axes_with_period_2026():
    """Test using period: 2026 in axes to avoid uprating"""
    situation = {
        "people": {"you": {"age": {2026: 35}}},
        "families": {"your family": {"members": ["you"]}},
        "spm_units": {"your household": {"members": ["you"]}},
        "tax_units": {"your tax unit": {"members": ["you"]}},
        "households": {
            "your household": {
                "members": ["you"],
                "state_name": {2026: "TX"}
            }
        },
        "axes": [
            [
                {
                    "name": "employment_income",
                    "count": 1001,
                    "min": 0,
                    "max": 1000000,
                    "period": 2026  # Specify period to avoid uprating
                }
            ]
        ]
    }

    sim = Simulation(situation=situation)
    income_range = sim.calculate("employment_income", map_to="household", period=2026)

    print(f"\nWith period=2026 in axes config:")
    print(f"First 10 values: {income_range[:10]}")
    print(f"Last 10 values: {income_range[-10:]}")
    print(f"Actual last value: {income_range[-1]:,.2f}")

    # Check if values are exact thousands
    errors = []
    for i in range(len(income_range)):
        expected = i * 1000
        actual = income_range[i]
        error = abs(actual - expected)
        if error > 1:  # More than $1 error
            errors.append((i, expected, actual, error))

    if errors:
        print(f"\nFound {len(errors)} values with >$1 error (first 10):")
        for i, exp, act, err in errors[:10]:
            print(f"  Index {i}: expected ${exp:,.0f}, got ${act:,.2f}, error ${err:,.2f}")
    else:
        print(f"\n✓ All {len(income_range)} values are exact 1k increments!")

    assert len(errors) == 0, f"Found {len(errors)} values with errors > $1"


def test_axes_with_uprating_compensation():
    """Test using compensated max to account for uprating"""
    # Use empirical uprating factor of ~1.09689
    # (The parameter lookup doesn't give us a simple multiplier)
    uprating = 1.09689

    # Calculate the max that will give us actual max of 1,000,000 after uprating
    compensated_max = round(1000000 / uprating)

    situation = {
        "people": {"you": {"age": {2026: 35}}},
        "families": {"your family": {"members": ["you"]}},
        "spm_units": {"your household": {"members": ["you"]}},
        "tax_units": {"your tax unit": {"members": ["you"]}},
        "households": {
            "your household": {
                "members": ["you"],
                "state_name": {2026: "TX"}
            }
        },
        "axes": [
            [
                {
                    "name": "employment_income",
                    "count": 1001,
                    "min": 0,
                    "max": compensated_max
                }
            ]
        ]
    }

    sim = Simulation(situation=situation)
    income_range = sim.calculate("employment_income", map_to="household", period=2026)

    print(f"\nWith compensated max={compensated_max:,.0f}:")
    print(f"First 10 values: {income_range[:10]}")
    print(f"Last 10 values: {income_range[-10:]}")
    print(f"Actual last value: {income_range[-1]:,.2f}")

    # Check if values are close to exact thousands
    errors = []
    for i in range(len(income_range)):
        expected = i * 1000
        actual = income_range[i]
        error = abs(actual - expected)
        if error > 1:  # More than $1 error
            errors.append((i, expected, actual, error))

    if errors:
        print(f"\nFound {len(errors)} values with >$1 error (first 10):")
        for i, exp, act, err in errors[:10]:
            print(f"  Index {i}: expected ${exp:,.0f}, got ${act:,.2f}, error ${err:,.2f}")
    else:
        print(f"\n✓ All {len(income_range)} values are within $1 of exact 1k increments!")

    assert len(errors) == 0, f"Found {len(errors)} values with errors > $1"
