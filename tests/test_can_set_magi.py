"""Test if we can set aca_magi directly."""
import sys
sys.path.insert(0, '.')

from policyengine_us import Simulation


def test_set_aca_magi():
    """Test if aca_magi can be set as input."""
    print("Testing if we can set aca_magi as input...")

    situation = {
        'people': {'p1': {'age': {2026: 35}}},
        'families': {'f1': {'members': ['p1']}},
        'spm_units': {'spm1': {'members': ['p1']}},
        'tax_units': {'tu1': {'members': ['p1'], 'aca_magi': {2026: 50000}}},
        'households': {'h1': {'members': ['p1'], 'state_name': {2026: 'TX'}}}
    }

    try:
        sim = Simulation(situation=situation)
        magi = sim.calculate('aca_magi', period=2026)[0]
        print(f"✓ Successfully set and retrieved aca_magi: ${magi:,.0f}")
    except Exception as e:
        print(f"✗ Cannot set aca_magi: {e}")
        return False

    return True


def test_set_employment_income():
    """Test traditional employment_income approach."""
    print("\nTesting employment_income approach...")

    situation = {
        'people': {'p1': {'age': {2026: 35}, 'employment_income': {2026: 50000}}},
        'families': {'f1': {'members': ['p1']}},
        'spm_units': {'spm1': {'members': ['p1']}},
        'tax_units': {'tu1': {'members': ['p1']}},
        'households': {'h1': {'members': ['p1'], 'state_name': {2026: 'TX'}}}
    }

    sim = Simulation(situation=situation)
    magi = sim.calculate('aca_magi', period=2026)[0]
    print(f"✓ Employment income → aca_magi: ${magi:,.0f}")


if __name__ == "__main__":
    if test_set_aca_magi():
        print("\n✅ aca_magi can be set directly!")
    else:
        print("\n⚠️ aca_magi cannot be set directly, must use income sources")

    test_set_employment_income()
