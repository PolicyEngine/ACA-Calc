from policyengine_us import Simulation
from policyengine_core.reforms import Reform

# Texas couple example from notebook - at 300% FPL ($63,450)
income = 63450
year = 2026

# Baseline household
household = {
    'people': {
        'you': {'age': {year: 25}, 'employment_income': {year: income/2}},
        'your partner': {'age': {year: 28}, 'employment_income': {year: income/2}}
    },
    'families': {'your family': {'members': ['you', 'your partner']}},
    'tax_units': {'your tax unit': {'members': ['you', 'your partner']}},
    'households': {
        'your household': {
            'members': ['you', 'your partner'],
            'state_name': {year: 'TX'}
        }
    },
    'marital_units': {'your marital unit': {'members': ['you', 'your partner']}}
}

# Create reform (IRA expires) - NOTE the key difference!
# The notebook has ptc_income_eligibility[2] = True which KEEPS eligibility above 400%
# We had it as False which REMOVES eligibility above 400%
reform = Reform.from_dict({
    'gov.aca.ptc_phase_out_rate[0].amount': {'2026-01-01.2100-12-31': 0},
    'gov.aca.ptc_phase_out_rate[1].amount': {'2026-01-01.2100-12-31': 0},
    'gov.aca.ptc_phase_out_rate[2].amount': {'2026-01-01.2100-12-31': 0},
    'gov.aca.ptc_phase_out_rate[3].amount': {'2026-01-01.2100-12-31': 0.02},
    'gov.aca.ptc_phase_out_rate[4].amount': {'2026-01-01.2100-12-31': 0.04},
    'gov.aca.ptc_phase_out_rate[5].amount': {'2026-01-01.2100-12-31': 0.06},
    'gov.aca.ptc_phase_out_rate[6].amount': {'2026-01-01.2100-12-31': 0.085},
    'gov.aca.ptc_income_eligibility[2].amount': {'2026-01-01.2100-12-31': True}  # THIS IS THE KEY!
}, country_id='us')

# Run simulations
sim_baseline = Simulation(situation=household)
sim_reform = Simulation(situation=household, reform=reform)

ptc_baseline = sim_baseline.calculate('aca_ptc', map_to='household', period=year)[0]
ptc_reform = sim_reform.calculate('aca_ptc', map_to='household', period=year)[0]

print(f'Texas couple at 300% FPL ($63,450):')
print(f'  PTC with IRA (baseline): ${ptc_baseline:,.2f}')
print(f'  PTC without IRA (reform): ${ptc_reform:,.2f}')
print(f'  Difference: ${ptc_baseline - ptc_reform:,.2f}')
print(f'\nNotebook expected: baseline=$4,062, reform=$6,283')
print(f'Match baseline: {abs(ptc_baseline - 4062) < 10}')
print(f'Match reform: {abs(ptc_reform - 6283) < 10}')

# Also test at 400% FPL
income_400 = 84600
household_400 = household.copy()
household_400['people']['you']['employment_income'] = {year: income_400/2}
household_400['people']['your partner']['employment_income'] = {year: income_400/2}

sim_400_baseline = Simulation(situation=household_400)
sim_400_reform = Simulation(situation=household_400, reform=reform)

ptc_400_baseline = sim_400_baseline.calculate('aca_ptc', map_to='household', period=year)[0]
ptc_400_reform = sim_400_reform.calculate('aca_ptc', map_to='household', period=year)[0]

print(f'\nTexas couple at 400% FPL ($84,600):')
print(f'  PTC with IRA (baseline): ${ptc_400_baseline:,.2f}')
print(f'  PTC without IRA (reform): ${ptc_400_reform:,.2f}')
print(f'  Notebook expected: baseline=$0, reform=$2,899')