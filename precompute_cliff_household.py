"""
Precompute the "cliff household" - single adult at 650% FPL in Lancaster County, PA.

This household demonstrates the ACA cliff dramatically:
- 2025 (IRA rules): Gets substantial PTC
- 2026 (baseline, no IRA): Gets $0 PTC (above 400% FPL cliff)
"""

import json
import numpy as np
import gc
from pathlib import Path
from policyengine_us import Simulation
from aca_calc.calculations.household import build_household_situation
from aca_calc.calculations.reforms import create_enhanced_ptc_reform, create_700fpl_reform


def main():
    output_dir = Path(__file__).parent / "data" / "households"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Precomputing cliff household (single adult, 650% FPL, Lebanon County PA)...")

    # Lebanon County has higher premiums than Lancaster, making the cliff more dramatic
    # ========== Build situations with income axes ==========
    situation_2025 = build_household_situation(
        age_head=45,
        age_spouse=None,
        dependent_ages=[],
        state="PA",
        county="Lebanon County",
        year=2025,
        with_axes=True,
    )

    situation_2026 = build_household_situation(
        age_head=45,
        age_spouse=None,
        dependent_ages=[],
        state="PA",
        county="Lebanon County",
        year=2026,
        with_axes=True,
    )

    # Run 2025 simulation (IRA is in effect)
    print("\n  Running 2025 simulation (IRA in effect)...")
    sim_2025 = Simulation(situation=situation_2025)
    income_2025 = sim_2025.calculate("employment_income", map_to="household", period=2025)
    ptc_2025 = sim_2025.calculate("aca_ptc", map_to="household", period=2025)
    slcsp_2025 = sim_2025.calculate("slcsp", map_to="household", period=2025)
    fpl_2025 = float(sim_2025.calculate("tax_unit_fpg", period=2025)[len(income_2025)//2])

    print(f"  FPL 2025: ${fpl_2025:,.0f}")

    # Run 2026 baseline simulation (IRA expires)
    print("\n  Running 2026 baseline simulation (IRA expires)...")
    sim_2026_baseline = Simulation(situation=situation_2026)
    income_2026 = sim_2026_baseline.calculate("employment_income", map_to="household", period=2026)
    ptc_2026_baseline = sim_2026_baseline.calculate("aca_ptc", map_to="household", period=2026)
    slcsp_2026 = sim_2026_baseline.calculate("slcsp", map_to="household", period=2026)
    fpl_2026 = float(sim_2026_baseline.calculate("tax_unit_fpg", period=2026)[len(income_2026)//2])

    # Also calculate Medicaid and CHIP for the health benefits chart
    medicaid_2026 = sim_2026_baseline.calculate("medicaid", map_to="household", period=2026)
    chip_2026 = sim_2026_baseline.calculate("chip", map_to="household", period=2026)

    print(f"  FPL 2026: ${fpl_2026:,.0f}")

    # Run 2026 with IRA extension
    print("\n  Running 2026 with IRA extension...")
    reform_ira = create_enhanced_ptc_reform()
    sim_2026_ira = Simulation(situation=situation_2026, reform=reform_ira)
    ptc_2026_ira = sim_2026_ira.calculate("aca_ptc", map_to="household", period=2026)

    # Run 2026 with 700% FPL bill
    print("\n  Running 2026 with 700% FPL bill...")
    reform_700fpl = create_700fpl_reform()
    ptc_2026_700fpl = None
    if reform_700fpl:
        sim_2026_700fpl = Simulation(situation=situation_2026, reform=reform_700fpl)
        ptc_2026_700fpl = sim_2026_700fpl.calculate("aca_ptc", map_to="household", period=2026)

    # Find income at 650% FPL
    target_income_2025 = fpl_2025 * 6.5
    target_income_2026 = fpl_2026 * 6.5
    print(f"\n  650% FPL income (2025): ${target_income_2025:,.0f}")
    print(f"  650% FPL income (2026): ${target_income_2026:,.0f}")

    # Find index closest to target income for 2025
    idx_2025 = np.argmin(np.abs(income_2025 - target_income_2025))
    actual_income_2025 = float(income_2025[idx_2025])
    ptc_at_650_2025 = float(ptc_2025[idx_2025])
    # Use max SLCSP since it can be 0 at certain income levels due to eligibility modeling
    max_slcsp_2025 = float(np.max(slcsp_2025))

    # Find index closest to target income for 2026
    idx_2026 = np.argmin(np.abs(income_2026 - target_income_2026))
    actual_income_2026 = float(income_2026[idx_2026])
    ptc_at_650_baseline = float(ptc_2026_baseline[idx_2026])
    ptc_at_650_ira = float(ptc_2026_ira[idx_2026])
    ptc_at_650_700fpl = float(ptc_2026_700fpl[idx_2026]) if ptc_2026_700fpl is not None else 0
    # Use max SLCSP since it can be 0 at certain income levels due to eligibility modeling
    max_slcsp_2026 = float(np.max(slcsp_2026))

    print(f"\n  Values at 650% FPL:")
    print(f"    2025 income: ${actual_income_2025:,.0f}")
    print(f"    2025 PTC (IRA): ${ptc_at_650_2025:,.0f}")
    print(f"    2025 SLCSP (max): ${max_slcsp_2025:,.0f}")
    print(f"    2026 income: ${actual_income_2026:,.0f}")
    print(f"    2026 PTC (baseline): ${ptc_at_650_baseline:,.0f}")
    print(f"    2026 PTC (IRA ext): ${ptc_at_650_ira:,.0f}")
    print(f"    2026 PTC (700% FPL): ${ptc_at_650_700fpl:,.0f}")
    print(f"    2026 SLCSP (max): ${max_slcsp_2026:,.0f}")

    # Build output data
    cliff_data = {
        "household_key": "cliff_demo",
        "household_info": {
            "name": "Pennsylvania Single Adult",
            "shortName": "PA Demo",
            "description": "Single adult (45) in Lebanon County, PA at 650% FPL",
            "location": "Lebanon County, PA",
            "age": 45,
            "state": "PA",
            "county": "Lebanon County",
            "fpl_percent": 650,
            "isExpansion": True,
        },
        "fpl_2025": fpl_2025,
        "fpl_2026": fpl_2026,
        # Full income sweep data for 2026 (for charts)
        "income": income_2026.tolist(),
        "medicaid": medicaid_2026.tolist(),
        "chip": chip_2026.tolist(),
        "ptc_baseline": ptc_2026_baseline.tolist(),
        "ptc_ira": ptc_2026_ira.tolist(),
        "ptc_700fpl": ptc_2026_700fpl.tolist() if ptc_2026_700fpl is not None else [],
        "slcsp": slcsp_2026.tolist(),
        "fpl": fpl_2026,
        # Specific values at 650% FPL for the demo
        "at_650_fpl": {
            "income_2025": actual_income_2025,
            "income_2026": actual_income_2026,
            "ptc_2025_ira": ptc_at_650_2025,
            "slcsp_2025": max_slcsp_2025,
            "ptc_2026_baseline": ptc_at_650_baseline,
            "ptc_2026_ira": ptc_at_650_ira,
            "ptc_2026_700fpl": ptc_at_650_700fpl,
            "slcsp_2026": max_slcsp_2026,
            "cliff_loss_annual": ptc_at_650_2025 - ptc_at_650_baseline,
            "cliff_loss_monthly": (ptc_at_650_2025 - ptc_at_650_baseline) / 12,
        },
        # Also include 2025 data for comparison charts
        "income_2025": income_2025.tolist(),
        "ptc_2025": ptc_2025.tolist(),
        "slcsp_2025": slcsp_2025.tolist(),
    }

    # Save
    output_file = output_dir / "cliff_demo.json"
    with open(output_file, "w") as f:
        json.dump(cliff_data, f, indent=2)
    print(f"\nSaved to {output_file}")

    # Print summary
    print("\n" + "=" * 70)
    print("CLIFF DEMO SUMMARY - Single Adult, Age 45, Lebanon County PA")
    print("=" * 70)
    print(f"\nIncome: ~${actual_income_2026:,.0f} (650% FPL)")
    print()
    print(f"{'Year':<8} {'Scenario':<25} {'PTC/year':<12} {'PTC/month':<12} {'SLCSP':<12}")
    print("-" * 70)
    print(f"{'2025':<8} {'IRA in effect':<25} ${ptc_at_650_2025:>9,.0f} ${ptc_at_650_2025/12:>9,.0f} ${max_slcsp_2025:>9,.0f}")
    print(f"{'2026':<8} {'Baseline (IRA expires)':<25} ${ptc_at_650_baseline:>9,.0f} ${ptc_at_650_baseline/12:>9,.0f} ${max_slcsp_2026:>9,.0f}")
    print(f"{'2026':<8} {'IRA Extended':<25} ${ptc_at_650_ira:>9,.0f} ${ptc_at_650_ira/12:>9,.0f} ${max_slcsp_2026:>9,.0f}")
    print(f"{'2026':<8} {'700% FPL Bill':<25} ${ptc_at_650_700fpl:>9,.0f} ${ptc_at_650_700fpl/12:>9,.0f} ${max_slcsp_2026:>9,.0f}")
    print()
    loss = ptc_at_650_2025 - ptc_at_650_baseline
    print(f"CLIFF IMPACT: This person loses ${loss:,.0f}/year (${loss/12:,.0f}/month) in subsidies")
    net_premium_2025 = max(0, max_slcsp_2025 - ptc_at_650_2025) / 12
    net_premium_2026 = max_slcsp_2026 / 12  # No PTC in baseline
    print(f"              Net premium jumps from ${net_premium_2025:,.0f}/mo to ${net_premium_2026:,.0f}/mo")

    gc.collect()


if __name__ == "__main__":
    main()
