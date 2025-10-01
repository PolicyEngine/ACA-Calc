"""Test ACA eligibility with different input methods."""
import sys
sys.path.insert(0, '.')

from policyengine_us import Simulation
from policyengine_core.reforms import Reform

reform = Reform.from_dict({
    "gov.aca.ptc_income_eligibility[2].amount": {"2026-01-01.2100-12-31": True}
}, country_id="us")

print("Testing 60yo couple at $85,000 income")

# Test 1: Setting aca_magi directly
print("\n=== Setting aca_magi directly ===")
sit1 = {
    'people': {'p1': {'age': {2026: 60}}, 'p2': {'age': {2026: 60}}},
    'families': {'f1': {'members': ['p1', 'p2']}},
    'marital_units': {'mu1': {'members': ['p1', 'p2']}},
    'spm_units': {'spm1': {'members': ['p1', 'p2']}},
    'tax_units': {'tu1': {'members': ['p1', 'p2'], 'aca_magi': {2026: 85000}}},
    'households': {'h1': {'members': ['p1', 'p2'], 'state_name': {2026: 'WV'}}}
}

sim1 = Simulation(situation=sit1, reform=reform)
eligible1 = sim1.calculate('is_aca_ptc_eligible', period=2026)
filing1 = sim1.calculate('filing_status', period=2026)
magi1 = sim1.calculate('aca_magi', period=2026)
ptc1 = sim1.calculate('aca_ptc', period=2026)

print(f"  Person 1 eligible: {eligible1[0]}")
print(f"  Person 2 eligible: {eligible1[1]}")
print(f"  Filing status: {filing1[0]}")
print(f"  MAGI: ${magi1[0]:,.0f}")
print(f"  PTC: ${ptc1[0]:,.0f}")

# Test 2: Setting employment_income
print("\n=== Setting employment_income ===")
sit2 = {
    'people': {
        'p1': {'age': {2026: 60}, 'employment_income': {2026: 42500}},
        'p2': {'age': {2026: 60}, 'employment_income': {2026: 42500}}
    },
    'families': {'f1': {'members': ['p1', 'p2']}},
    'marital_units': {'mu1': {'members': ['p1', 'p2']}},
    'spm_units': {'spm1': {'members': ['p1', 'p2']}},
    'tax_units': {'tu1': {'members': ['p1', 'p2']}},
    'households': {'h1': {'members': ['p1', 'p2'], 'state_name': {2026: 'WV'}}}
}

sim2 = Simulation(situation=sit2, reform=reform)
eligible2 = sim2.calculate('is_aca_ptc_eligible', period=2026)
filing2 = sim2.calculate('filing_status', period=2026)
magi2 = sim2.calculate('aca_magi', period=2026)
ptc2 = sim2.calculate('aca_ptc', period=2026)

print(f"  Person 1 eligible: {eligible2[0]}")
print(f"  Person 2 eligible: {eligible2[1]}")
print(f"  Filing status: {filing2[0]}")
print(f"  MAGI: ${magi2[0]:,.0f}")
print(f"  PTC: ${ptc2[0]:,.0f}")
