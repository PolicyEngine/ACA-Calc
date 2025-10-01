"""Simple cliff test."""
import sys
sys.path.insert(0, '.')

from policyengine_us import Simulation
from policyengine_core.reforms import Reform
from app import get_fpl

# 60yo couple in WV
fpl_2 = get_fpl(2)
income_at_405_fpl = int(fpl_2 * 4.05)

print(f"FPL for 2 people: ${fpl_2:,}")
print(f"405% FPL: ${income_at_405_fpl:,}")

situation = {
    'people': {
        'p1': {'age': {2026: 60}},
        'p2': {'age': {2026: 60}}
    },
    'families': {'f1': {'members': ['p1', 'p2']}},
    'marital_units': {'mu1': {'members': ['p1', 'p2']}},
    'spm_units': {'spm1': {'members': ['p1', 'p2']}},
    'tax_units': {'tu1': {'members': ['p1', 'p2'], 'aca_magi': {2026: income_at_405_fpl}}},
    'households': {'h1': {'members': ['p1', 'p2'], 'state_name': {2026: 'WV'}}}
}

# Test baseline (should be $0 above 400% FPL)
print("\n=== BASELINE (no reform) ===")
sim_baseline = Simulation(situation=situation)
ptc_baseline = sim_baseline.calculate('aca_ptc', period=2026)[0]
print(f"PTC at 405% FPL: ${ptc_baseline:,.0f}")

# Test with reform (should have PTC above 400% FPL)
print("\n=== WITH REFORM ===")
reform = Reform.from_dict({
    "gov.aca.ptc_phase_out_rate[0].amount": {"2026-01-01.2100-12-31": 0},
    "gov.aca.ptc_phase_out_rate[1].amount": {"2025-01-01.2100-12-31": 0},
    "gov.aca.ptc_phase_out_rate[2].amount": {"2026-01-01.2100-12-31": 0},
    "gov.aca.ptc_phase_out_rate[3].amount": {"2026-01-01.2100-12-31": 0.02},
    "gov.aca.ptc_phase_out_rate[4].amount": {"2026-01-01.2100-12-31": 0.04},
    "gov.aca.ptc_phase_out_rate[5].amount": {"2026-01-01.2100-12-31": 0.06},
    "gov.aca.ptc_phase_out_rate[6].amount": {"2026-01-01.2100-12-31": 0.085},
    "gov.aca.ptc_income_eligibility[2].amount": {"2026-01-01.2100-12-31": True}
}, country_id="us")

sim_reform = Simulation(situation=situation, reform=reform)
ptc_reform = sim_reform.calculate('aca_ptc', period=2026)[0]
print(f"PTC at 405% FPL: ${ptc_reform:,.0f}")

print("\n" + "="*70)
if ptc_baseline == 0 and ptc_reform > 0:
    print("✓ CLIFF WORKS: Baseline=$0, Reform>$0 above 400% FPL")
else:
    print(f"✗ CLIFF BROKEN: Baseline=${ptc_baseline:,.0f}, Reform=${ptc_reform:,.0f}")
