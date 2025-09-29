from policyengine_us import Simulation
from policyengine_core.reforms import Reform

# Test household at 300% FPL (should get credits in both scenarios)
household = {
    'people': {'you': {'age': {2026: 30}, 'employment_income': {2026: 31650}}},
    'families': {'your family': {'members': ['you']}},
    'tax_units': {'your tax unit': {'members': ['you']}},
    'households': {'your household': {'members': ['you'], 'state_name': {2026: 'TX'}}}
}

# Baseline (current law - IRA still in effect in 2026)
sim_baseline = Simulation(situation=household)
ptc_baseline = sim_baseline.calculate('aca_ptc', map_to='household', period=2026)[0]

# Reform that reinstates 400% cap (original ACA)
reform = Reform.from_dict({
    'gov.aca.ptc_phase_out_rate[0].amount': {'2026-01-01.2100-12-31': 0},
    'gov.aca.ptc_phase_out_rate[1].amount': {'2026-01-01.2100-12-31': 0},
    'gov.aca.ptc_phase_out_rate[2].amount': {'2026-01-01.2100-12-31': 0},
    'gov.aca.ptc_phase_out_rate[3].amount': {'2026-01-01.2100-12-31': 0.02},
    'gov.aca.ptc_phase_out_rate[4].amount': {'2026-01-01.2100-12-31': 0.04},
    'gov.aca.ptc_phase_out_rate[5].amount': {'2026-01-01.2100-12-31': 0.06},
    'gov.aca.ptc_phase_out_rate[6].amount': {'2026-01-01.2100-12-31': 0.085},
    'gov.aca.ptc_income_eligibility[2].amount': {'2026-01-01.2100-12-31': False}  # Reinstates 400% cap
}, country_id='us')

sim_reform = Simulation(situation=household, reform=reform)
ptc_reform = sim_reform.calculate('aca_ptc', map_to='household', period=2026)[0]

print('Single person at 300% FPL in TX:')
print(f'  Current law (IRA enhanced): ${ptc_baseline:,.2f}')
print(f'  After expiration (original ACA): ${ptc_reform:,.2f}')
print(f'  Person LOSES: ${ptc_baseline - ptc_reform:,.2f} when IRA expires')

# Test at 450% FPL (above the cliff)
household_450 = household.copy()
household_450['people']['you']['employment_income'] = {2026: 70000}

sim_450_base = Simulation(situation=household_450)
sim_450_reform = Simulation(situation=household_450, reform=reform)

ptc_450_base = sim_450_base.calculate('aca_ptc', map_to='household', period=2026)[0]
ptc_450_reform = sim_450_reform.calculate('aca_ptc', map_to='household', period=2026)[0]

print('\nSingle person at ~450% FPL in TX:')
print(f'  Current law (IRA enhanced): ${ptc_450_base:,.2f}')
print(f'  After expiration (original ACA): ${ptc_450_reform:,.2f}')
print(f'  Person LOSES: ${ptc_450_base:,.2f} when IRA expires (the cliff!)')

print('\n' + '='*60)
print('LABEL CHECK:')
print('- Baseline = Current law with IRA enhancements (NO cap)')
print('- Reform = Original ACA rules (400% FPL cap)')
print('- Our app shows what people LOSE when IRA expires')
print('='*60)