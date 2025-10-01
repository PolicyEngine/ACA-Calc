"""Test the 400% FPL cliff."""
import sys
sys.path.insert(0, '.')

from app import calculate_ptc, get_fpl


def test_cliff_at_400_fpl():
    """Test that baseline has cliff at 400% FPL but reform doesn't."""

    # 60-year-old couple in WV
    household_size = 2
    fpl = get_fpl(household_size)

    print(f"2-person FPL: ${fpl:,}")
    print(f"400% FPL: ${fpl * 4:,}")

    # Test just below 400% FPL
    income_below = int(fpl * 3.99)
    print(f"\nTesting at 399% FPL (${income_below:,}):")

    ptc_reform_below, slcsp = calculate_ptc(60, 60, income_below, [], "WV", None, use_reform=True)
    ptc_baseline_below, _ = calculate_ptc(60, 60, income_below, [], "WV", None, use_reform=False)

    print(f"  Baseline PTC: ${ptc_baseline_below:,.0f}")
    print(f"  Reform PTC: ${ptc_reform_below:,.0f}")

    # Test at 400% FPL
    income_at = int(fpl * 4.0)
    print(f"\nTesting at 400% FPL (${income_at:,}):")

    ptc_reform_at, _ = calculate_ptc(60, 60, income_at, [], "WV", None, use_reform=True)
    ptc_baseline_at, _ = calculate_ptc(60, 60, income_at, [], "WV", None, use_reform=False)

    print(f"  Baseline PTC: ${ptc_baseline_at:,.0f}")
    print(f"  Reform PTC: ${ptc_reform_at:,.0f}")

    # Test above 400% FPL
    income_above = int(fpl * 4.5)
    print(f"\nTesting at 450% FPL (${income_above:,}):")

    ptc_reform_above, _ = calculate_ptc(60, 60, income_above, [], "WV", None, use_reform=True)
    ptc_baseline_above, _ = calculate_ptc(60, 60, income_above, [], "WV", None, use_reform=False)

    print(f"  Baseline PTC: ${ptc_baseline_above:,.0f}")
    print(f"  Reform PTC: ${ptc_reform_above:,.0f}")

    print("\n" + "="*70)
    print("VERIFICATION:")
    print("="*70)

    # Baseline should be $0 above 400% FPL
    if ptc_baseline_above == 0:
        print("✓ Baseline correctly has cliff (PTC = $0 above 400% FPL)")
    else:
        print(f"✗ FAIL: Baseline should be $0 above 400% FPL, got ${ptc_baseline_above:,.0f}")

    # Reform should still have PTC above 400% FPL
    if ptc_reform_above > 0:
        print("✓ Reform correctly has no cliff (PTC > $0 above 400% FPL)")
    else:
        print(f"✗ FAIL: Reform should have PTC above 400% FPL, got ${ptc_reform_above:,.0f}")


if __name__ == "__main__":
    test_cliff_at_400_fpl()
