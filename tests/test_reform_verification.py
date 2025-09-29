"""
Verify that the reform is actually being applied in the app's calculate_ptc function
"""
from policyengine_us import Simulation
from policyengine_core.reforms import Reform

# Texas couple at 300% FPL - from notebook
household = {
    "people": {
        "you": {
            "age": {2026: 25},
            "employment_income": {2026: 31725}  # Split $63,450
        },
        "your partner": {
            "age": {2026: 28},
            "employment_income": {2026: 31725}
        }
    },
    "families": {"your family": {"members": ["you", "your partner"]}},
    "spm_units": {"your household": {"members": ["you", "your partner"]}},
    "tax_units": {"your tax unit": {"members": ["you", "your partner"]}},
    "households": {
        "your household": {
            "members": ["you", "your partner"],
            "state_name": {2026: "TX"},
            "county_fips": {2026: "48015"}
        }
    },
    "marital_units": {"your marital unit": {"members": ["you", "your partner"]}}
}

print("="*60)
print("VERIFYING REFORM APPLICATION")
print("Texas couple at 300% FPL ($63,450)")
print("="*60)

# Baseline (no reform)
sim_baseline = Simulation(situation=household)
ptc_baseline = sim_baseline.calculate("aca_ptc", map_to="household", period=2026)[0]
slcsp = sim_baseline.calculate("slcsp", map_to="household", period=2026)[0]

print(f"\n1. BASELINE (Original ACA for 2026):")
print(f"   PTC: ${ptc_baseline:,.2f}")
print(f"   SLCSP: ${slcsp:,.2f}")

# Reform (IRA extension)
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

sim_reform = Simulation(situation=household, reform=reform)
ptc_reform = sim_reform.calculate("aca_ptc", map_to="household", period=2026)[0]

print(f"\n2. WITH REFORM (IRA extension to 2026):")
print(f"   PTC: ${ptc_reform:,.2f}")
print(f"   SLCSP: ${slcsp:,.2f}")

print(f"\n3. DIFFERENCE:")
print(f"   Reform PTC - Baseline PTC = ${ptc_reform - ptc_baseline:,.2f}")
print(f"   (Reform should be HIGHER)")

print(f"\n4. EXPECTED FROM NOTEBOOK:")
print(f"   Baseline: $4,062")
print(f"   Reform: $6,283")
print(f"   Difference: $2,221")

print(f"\n5. MATCH CHECK:")
baseline_match = abs(ptc_baseline - 4062) < 50
reform_match = abs(ptc_reform - 6283) < 50
print(f"   Baseline matches: {'✓' if baseline_match else '✗'} (${ptc_baseline:,.0f} vs $4,062)")
print(f"   Reform matches: {'✓' if reform_match else '✗'} (${ptc_reform:,.0f} vs $6,283)")

if baseline_match and reform_match:
    print(f"\n✓ SUCCESS: Reform is working correctly!")
else:
    print(f"\n✗ ISSUE: Values don't match expected")

# Now test with 400% FPL - where the cliff happens
print("\n" + "="*60)
print("TESTING 400% FPL ($84,600) - THE CLIFF")
print("="*60)

household_400 = household.copy()
household_400["people"]["you"]["employment_income"] = {2026: 42300}
household_400["people"]["your partner"]["employment_income"] = {2026: 42300}

sim_baseline_400 = Simulation(situation=household_400)
ptc_baseline_400 = sim_baseline_400.calculate("aca_ptc", map_to="household", period=2026)[0]

sim_reform_400 = Simulation(situation=household_400, reform=reform)
ptc_reform_400 = sim_reform_400.calculate("aca_ptc", map_to="household", period=2026)[0]

print(f"\nBaseline PTC: ${ptc_baseline_400:,.2f} (should be $0 - above cliff)")
print(f"Reform PTC: ${ptc_reform_400:,.2f} (should be ~$2,899 - no cliff)")
print(f"\nExpected from notebook: Baseline=$0, Reform=$2,899")

cliff_test = ptc_baseline_400 == 0 and abs(ptc_reform_400 - 2899) < 50
print(f"\n✓ Cliff test: {'PASS' if cliff_test else 'FAIL'}")