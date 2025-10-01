"""Test using aca_magi as an axis."""
import sys
sys.path.insert(0, '.')

from policyengine_us import Simulation


def test_aca_magi_axis():
    """Test using aca_magi as axis variable."""
    print("Testing aca_magi as axis...")

    situation = {
        'people': {'p1': {'age': {2026: 35}}},
        'families': {'f1': {'members': ['p1']}},
        'spm_units': {'spm1': {'members': ['p1']}},
        'tax_units': {'tu1': {'members': ['p1']}},
        'households': {'h1': {'members': ['p1'], 'state_name': {2026: 'TX'}}},
        'axes': [[{
            'name': 'aca_magi',
            'period': 2026,
            'count': 5,
            'min': 0,
            'max': 100000
        }]]
    }

    try:
        sim = Simulation(situation=situation)
        magi_range = sim.calculate('aca_magi', map_to='household', period=2026)
        print(f"✓ aca_magi as axis works!")
        print(f"  Income range: ${magi_range[0]:,.0f} to ${magi_range[-1]:,.0f}")
        print(f"  Values: {[f'${x:,.0f}' for x in magi_range]}")
        return True
    except Exception as e:
        print(f"✗ aca_magi as axis failed: {e}")
        return False


def test_employment_income_axis():
    """Test using employment_income as axis."""
    print("\nTesting employment_income as axis...")

    situation = {
        'people': {'p1': {'age': {2026: 35}}},
        'families': {'f1': {'members': ['p1']}},
        'spm_units': {'spm1': {'members': ['p1']}},
        'tax_units': {'tu1': {'members': ['p1']}},
        'households': {'h1': {'members': ['p1'], 'state_name': {2026: 'TX'}}},
        'axes': [[{
            'name': 'employment_income',
            'count': 5,
            'min': 0,
            'max': 100000
        }]]
    }

    sim = Simulation(situation=situation)
    income_range = sim.calculate('employment_income', map_to='household', period=2026)
    magi_range = sim.calculate('aca_magi', map_to='household', period=2026)

    print(f"✓ employment_income as axis works!")
    print(f"  Employment income: ${income_range[0]:,.0f} to ${income_range[-1]:,.0f}")
    print(f"  Resulting MAGI: ${magi_range[0]:,.0f} to ${magi_range[-1]:,.0f}")


if __name__ == "__main__":
    can_use_magi = test_aca_magi_axis()
    test_employment_income_axis()

    if not can_use_magi:
        print("\n⚠️  aca_magi cannot be used as axis - need to use employment_income")
