"""Test basic PolicyEngine US functionality."""
import sys
sys.path.insert(0, '.')

from policyengine_us import Simulation


def test_basic_simulation():
    """Test that basic simulation works."""
    print("Testing basic PolicyEngine US simulation...")

    situation = {
        'people': {
            'person1': {
                'age': {2026: 35},
                'employment_income': {2026: 50000}
            }
        },
        'families': {'family1': {'members': ['person1']}},
        'spm_units': {'spm_unit1': {'members': ['person1']}},
        'tax_units': {'tax_unit1': {'members': ['person1']}},
        'households': {
            'household1': {
                'members': ['person1'],
                'state_name': {2026: 'TX'}
            }
        }
    }

    sim = Simulation(situation=situation)

    # List available variables
    print("\nAvailable variables:")
    all_vars = list(sim.tax_benefit_system.variables.keys())

    # Find health/ACA related variables
    health_vars = [v for v in all_vars if any(keyword in v.lower() for keyword in ['health', 'aca', 'premium', 'slcsp', 'medicaid', 'chip'])]

    print(f"Found {len(health_vars)} health-related variables:")
    for v in sorted(health_vars)[:30]:
        print(f"  - {v}")

    # Try to calculate income
    income = sim.calculate('employment_income', period=2026)
    print(f"\nIncome: ${income[0]:,.0f}")

    print("\n✓ Basic simulation works")


if __name__ == "__main__":
    test_basic_simulation()
