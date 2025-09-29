"""
Test the actual calculate_ptc function from app.py to see what's wrong
"""
from policyengine_us import Simulation
from policyengine_core.reforms import Reform

def calculate_ptc(age_head, age_spouse, income, dependent_ages, state, use_reform=False):
    """Calculate PTC for baseline or IRA enhanced scenario using 2026 comparison"""
    try:
        # Build household for 2026
        household = {
            "people": {
                "you": {"age": {2026: age_head}}
            },
            "families": {"your family": {"members": ["you"]}},
            "spm_units": {"your household": {"members": ["you"]}},
            "tax_units": {"your tax unit": {"members": ["you"]}},
            "households": {
                "your household": {
                    "members": ["you"],
                    "state_name": {2026: state},
                    "county_fips": {2026: "48015"}  # Default to Austin, TX like notebook
                }
            }
        }

        # Add income and spouse
        if age_spouse:
            household["people"]["you"]["employment_income"] = {2026: income / 2}
            household["people"]["your partner"] = {
                "age": {2026: age_spouse},
                "employment_income": {2026: income / 2}
            }
            household["families"]["your family"]["members"].append("your partner")
            household["spm_units"]["your household"]["members"].append("your partner")
            household["tax_units"]["your tax unit"]["members"].append("your partner")
            household["households"]["your household"]["members"].append("your partner")
            household["marital_units"] = {"your marital unit": {"members": ["you", "your partner"]}}
        else:
            household["people"]["you"]["employment_income"] = {2026: income}

        # Add dependents with proper marital unit structure
        for i, dep_age in enumerate(dependent_ages):
            child_id = f"your child {i+1}" if i == 0 else f"your child {i+1}"
            if i == 0:
                child_id = "your first dependent"
            elif i == 1:
                child_id = "your second dependent"
            else:
                child_id = f"child_{i+1}"

            household["people"][child_id] = {"age": {2026: dep_age}}
            household["families"]["your family"]["members"].append(child_id)
            household["spm_units"]["your household"]["members"].append(child_id)
            household["tax_units"]["your tax unit"]["members"].append(child_id)
            household["households"]["your household"]["members"].append(child_id)

            # Add child's marital unit
            if "marital_units" not in household:
                household["marital_units"] = {}
            household["marital_units"][f"{child_id}'s marital unit"] = {
                "members": [child_id],
                "marital_unit_id": {2026: i + (2 if age_spouse else 1)}
            }

        # Create reform for IRA enhancements (exactly from notebook)
        if use_reform:
            try:
                from policyengine_core.reforms import Reform
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
                sim = Simulation(situation=household, reform=reform)
            except ImportError:
                # Fallback if reform import fails
                sim = Simulation(situation=household)
        else:
            # Baseline - original ACA rules for 2026
            sim = Simulation(situation=household)

        ptc = sim.calculate("aca_ptc", map_to="household", period=2026)[0]
        slcsp = sim.calculate("slcsp", map_to="household", period=2026)[0]

        return float(max(0, ptc)), float(slcsp)

    except Exception as e:
        print(f"Calculation error: {str(e)}")
        return 0, 0

# Test with Texas couple at 300% FPL
print("="*60)
print("TESTING APP'S calculate_ptc FUNCTION")
print("Texas couple at 300% FPL ($63,450)")
print("="*60)

ptc_baseline, slcsp = calculate_ptc(
    age_head=25,
    age_spouse=28,
    income=63450,
    dependent_ages=[],
    state="TX",
    use_reform=False
)

ptc_reform, _ = calculate_ptc(
    age_head=25,
    age_spouse=28,
    income=63450,
    dependent_ages=[],
    state="TX",
    use_reform=True
)

print(f"\nBaseline PTC: ${ptc_baseline:,.2f}")
print(f"Reform PTC: ${ptc_reform:,.2f}")
print(f"SLCSP: ${slcsp:,.2f}")
print(f"Difference: ${ptc_reform - ptc_baseline:,.2f}")

print(f"\nExpected: Baseline=$4,062, Reform=$6,283, Diff=$2,221")
print(f"Match: {'✓' if abs(ptc_baseline - 4062) < 50 and abs(ptc_reform - 6283) < 50 else '✗'}")

# Test with 400% FPL
print("\n" + "="*60)
print("TESTING 400% FPL ($84,600) - THE CLIFF")
print("="*60)

ptc_baseline_400, _ = calculate_ptc(
    age_head=25,
    age_spouse=28,
    income=84600,
    dependent_ages=[],
    state="TX",
    use_reform=False
)

ptc_reform_400, _ = calculate_ptc(
    age_head=25,
    age_spouse=28,
    income=84600,
    dependent_ages=[],
    state="TX",
    use_reform=True
)

print(f"\nBaseline PTC: ${ptc_baseline_400:,.2f} (should be $0)")
print(f"Reform PTC: ${ptc_reform_400:,.2f} (should be ~$2,899)")
print(f"Match: {'✓' if ptc_baseline_400 == 0 and abs(ptc_reform_400 - 2899) < 50 else '✗'}")

# Test with single person
print("\n" + "="*60)
print("TESTING SINGLE PERSON, NJ, $50k")
print("="*60)

ptc_baseline_single, slcsp_single = calculate_ptc(
    age_head=35,
    age_spouse=None,
    income=50000,
    dependent_ages=[],
    state="NJ",
    use_reform=False
)

ptc_reform_single, _ = calculate_ptc(
    age_head=35,
    age_spouse=None,
    income=50000,
    dependent_ages=[],
    state="NJ",
    use_reform=True
)

print(f"\nBaseline PTC: ${ptc_baseline_single:,.2f}")
print(f"Reform PTC: ${ptc_reform_single:,.2f}")
print(f"SLCSP: ${slcsp_single:,.2f}")
print(f"Difference: ${ptc_reform_single - ptc_baseline_single:,.2f}")

print("\n" + "="*60)
print("CONCLUSION:")
if all([
    abs(ptc_baseline - 4062) < 50,
    abs(ptc_reform - 6283) < 50,
    ptc_baseline_400 == 0,
    abs(ptc_reform_400 - 2899) < 50
]):
    print("✓ The app's calculate_ptc function works correctly!")
    print("The issue must be somewhere else in the app.")
else:
    print("✗ The app's calculate_ptc function has issues.")
print("="*60)