"""Test that we can get FPL values from PolicyEngine instead of hardcoding"""
from policyengine_us import Simulation


def test_get_fpl_from_policyengine():
    """Test getting FPL values from PolicyEngine"""
    # Test for household size of 4
    situation = {
        "people": {
            "you": {"age": {2026: 35}},
            "partner": {"age": {2026: 35}},
            "child1": {"age": {2026: 10}},
            "child2": {"age": {2026: 8}}
        },
        "families": {"your family": {"members": ["you", "partner", "child1", "child2"]}},
        "spm_units": {"your household": {"members": ["you", "partner", "child1", "child2"]}},
        "tax_units": {"your tax unit": {"members": ["you", "partner", "child1", "child2"]}},
        "households": {
            "your household": {
                "members": ["you", "partner", "child1", "child2"],
                "state_name": {2026: "TX"}
            }
        }
    }

    sim = Simulation(situation=situation)

    # Get FPL from PolicyEngine
    fpl = sim.calculate("tax_unit_fpg", period=2026)[0]
    print(f"\nFPL for household of 4 in TX (2026): ${fpl:,.0f}")

    # Get ACA MAGI fraction
    # Set some income first
    situation["people"]["you"]["employment_income"] = {2026: 50000}
    sim = Simulation(situation=situation)

    fpl = sim.calculate("tax_unit_fpg", period=2026)[0]
    magi = sim.calculate("aca_magi", period=2026)[0]
    magi_fraction = sim.calculate("aca_magi_fraction", period=2026)[0]

    print(f"\nWith $50k employment income:")
    print(f"  ACA MAGI: ${magi:,.0f}")
    print(f"  FPL: ${fpl:,.0f}")
    print(f"  MAGI fraction (from PE): {magi_fraction:.2f}")
    print(f"  MAGI % of FPL (calculated): {(magi / fpl * 100):.1f}%")
    print(f"  MAGI % from fraction * 100: {(magi_fraction * 100):.1f}%")

    assert fpl > 0, "FPL should be positive"
    assert magi > 0, "MAGI should be positive"


def test_compare_hardcoded_vs_policyengine_fpl():
    """Compare our hardcoded FPL values to PolicyEngine"""
    # Hardcoded values from app.py
    fpl_hardcoded = {
        1: 15570,
        2: 21130,
        3: 26650,
        4: 32200,
        5: 37750,
        6: 43300,
        7: 48850,
        8: 54400,
    }

    for size in range(1, 9):
        situation = {
            "people": {f"person{i}": {"age": {2026: 30}} for i in range(size)},
            "families": {"fam": {"members": [f"person{i}" for i in range(size)]}},
            "spm_units": {"spm": {"members": [f"person{i}" for i in range(size)]}},
            "tax_units": {"tu": {"members": [f"person{i}" for i in range(size)]}},
            "households": {
                "hh": {
                    "members": [f"person{i}" for i in range(size)],
                    "state_name": {2026: "TX"}
                }
            }
        }

        sim = Simulation(situation=situation)
        fpl_pe = sim.calculate("tax_unit_fpg", period=2026)[0]
        fpl_hard = fpl_hardcoded[size]

        print(f"\nSize {size}: Hardcoded=${fpl_hard:,} PolicyEngine=${fpl_pe:,.0f} Diff=${(fpl_pe - fpl_hard):,.0f}")

        # They should be close (might differ by year)
        # Let's just check they're in the same ballpark (within 20%)
        assert abs(fpl_pe - fpl_hard) / fpl_hard < 0.2, f"FPL values differ too much for size {size}"


if __name__ == "__main__":
    test_get_fpl_from_policyengine()
    print("\n" + "="*80)
    test_compare_hardcoded_vs_policyengine_fpl()
