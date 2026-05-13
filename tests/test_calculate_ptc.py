"""Test the reusable Premium Tax Credit calculation helper."""

from aca_calc.calculations.ptc import calculate_ptc


def test_simple_calculation():
    """Test a simple PTC calculation."""
    print("Testing simple single person calculation...")

    # Single person, age 35, $50,000 income in TX
    ptc_reform, slcsp, _fpl, _fpl_pct = calculate_ptc(
        age_head=35,
        age_spouse=None,
        income=50000,
        dependent_ages=[],
        state="TX",
        county_name=None,
        use_reform=True,
    )

    print(f"Reform PTC: ${ptc_reform:,.0f}")
    print(f"SLCSP: ${slcsp:,.0f}")

    # Should get some PTC and SLCSP > 0
    assert slcsp > 0, f"SLCSP should be > 0, got {slcsp}"
    assert ptc_reform >= 0, f"PTC should be >= 0, got {ptc_reform}"

    print("✓ Simple calculation works")


def test_baseline_vs_reform():
    """Test baseline vs reform calculation."""
    print("\nTesting baseline vs reform...")

    # Couple at 300% FPL
    ptc_reform, slcsp, _fpl, _fpl_pct = calculate_ptc(
        age_head=25,
        age_spouse=28,
        income=63450,
        dependent_ages=[],
        state="TX",
        county_name=None,
        use_reform=True,
    )

    ptc_baseline, _, _, _ = calculate_ptc(
        age_head=25,
        age_spouse=28,
        income=63450,
        dependent_ages=[],
        state="TX",
        county_name=None,
        use_reform=False,
    )

    print(f"Reform PTC: ${ptc_reform:,.0f}")
    print(f"Baseline PTC: ${ptc_baseline:,.0f}")
    print(f"SLCSP: ${slcsp:,.0f}")

    assert slcsp > 0, "SLCSP should be > 0"
    # Reform should give more credits than baseline at 300% FPL
    assert (
        ptc_reform >= ptc_baseline
    ), f"Reform ({ptc_reform}) should be >= baseline ({ptc_baseline})"

    print("✓ Baseline vs reform works")
