"""Test employment_income vs aca_magi input."""
import sys
sys.path.insert(0, '.')

from policyengine_us import Simulation
from policyengine_core.reforms import Reform
from app import get_fpl

fpl_2 = get_fpl(2)
income = int(fpl_2 * 4.05)

print(f"Testing 60yo couple at 405% FPL (${income:,})")

reform = Reform.from_dict({
    "gov.aca.ptc_income_eligibility[2].amount": {"2026-01-01.2100-12-31": True}
}, country_id="us")

# Test 1: Setting aca_magi directly
print("\n=== Setting aca_magi directly ===")
sit1 = {
    'people': {'p1': {'age': {2026: 60}}, 'p2': {'age': {2026: 60}}},
    'families': {'f1': {'members': ['p1', 'p2']}},
    'marital_units': {'mu1': {'members': ['p1', 'p2']}},
    'spm_units': {'spm1': {'members': ['p1', 'p2']}},
    'tax_units': {'tu1': {'members': ['p1', 'p2'], 'aca_magi': {2026: income}}},
    'households': {'h1': {'members': ['p1', 'p2'], 'state_name': {2026: 'WV'}}}
}

sim1 = Simulation(situation=sit1, reform=reform)
ptc1 = sim1.calculate('aca_ptc', period=2026)[0]
print(f"PTC with reform: ${ptc1:,.0f}")

# Test 2: Setting employment_income
print("\n=== Setting employment_income ===")
sit2 = {
    'people': {
        'p1': {'age': {2026: 60}, 'employment_income': {2026: income/2}},
        'p2': {'age': {2026: 60}, 'employment_income': {2026: income/2}}
    },
    'families': {'f1': {'members': ['p1', 'p2']}},
    'marital_units': {'mu1': {'members': ['p1', 'p2']}},
    'spm_units': {'spm1': {'members': ['p1', 'p2']}},
    'tax_units': {'tu1': {'members': ['p1', 'p2']}},
    'households': {'h1': {'members': ['p1', 'p2'], 'state_name': {2026: 'WV'}}}
}

sim2 = Simulation(situation=sit2, reform=reform)
ptc2 = sim2.calculate('aca_ptc', period=2026)[0]
magi2 = sim2.calculate('aca_magi', period=2026)[0]
print(f"Calculated MAGI: ${magi2:,.0f}")
print(f"PTC with reform: ${ptc2:,.0f}")

print("\n" + "="*70)
if ptc2 > 0:
    print(f"✓ employment_income approach works: PTC = ${ptc2:,.0f}")
    print("✗ aca_magi direct setting doesn't work for reforms")
else:
    print("✗ Neither approach works!")
