from policyengine_us import Simulation

# New Jersey, Essex County, 35 year old, $50k income
household = {
    "people": {
        "you": {
            "age": {
                2025: 35,
                2026: 36  # Will be 36 in 2026
            },
            "employment_income": {
                2025: 50000,
                2026: 50000
            }
        }
    },
    "families": {
        "your family": {
            "members": ["you"]
        }
    },
    "tax_units": {
        "your tax unit": {
            "members": ["you"]
        }
    },
    "households": {
        "your household": {
            "members": ["you"],
            "state_name": {
                2025: "NJ",
                2026: "NJ"
            }
        }
    }
}

# Calculate for 2025 (with IRA enhancements)
sim_2025 = Simulation(situation=household)
ptc_2025 = sim_2025.calculate("aca_ptc", map_to="household", period=2025)[0]
slcsp_2025 = sim_2025.calculate("slcsp", map_to="household", period=2025)[0]

# Calculate for 2026 (after IRA expires)
sim_2026 = Simulation(situation=household)
ptc_2026 = sim_2026.calculate("aca_ptc", map_to="household", period=2026)[0]
slcsp_2026 = sim_2026.calculate("slcsp", map_to="household", period=2026)[0]

# Calculate FPL percentage
fpl_2026 = 15570  # Single person FPL
fpl_pct = (50000 / fpl_2026) * 100

print("="*60)
print("NEW JERSEY - ESSEX COUNTY")
print("35 year old, single, $50,000 income")
print("="*60)
print(f"\nIncome as % of FPL: {fpl_pct:.0f}%")
print(f"\nBenchmark Plan (SLCSP):")
print(f"  2025: ${slcsp_2025:,.2f}/year")
print(f"  2026: ${slcsp_2026:,.2f}/year")

print(f"\nPremium Tax Credit:")
print(f"  2025 (with IRA):     ${ptc_2025:,.2f}/year (${ptc_2025/12:,.2f}/month)")
print(f"  2026 (after expire): ${ptc_2026:,.2f}/year (${ptc_2026/12:,.2f}/month)")

difference = ptc_2025 - ptc_2026
print(f"\nIMPACT OF IRA EXPIRATION:")
if difference > 0:
    print(f"  Loss: ${difference:,.2f}/year (${difference/12:,.2f}/month)")
    print(f"  This person will pay ${difference/12:,.2f} more per month for health insurance")
elif difference < 0:
    print(f"  Gain: ${abs(difference):,.2f}/year (${abs(difference)/12:,.2f}/month)")
else:
    print(f"  No change")

# Calculate what percentage of income they pay
if ptc_2025 > 0:
    contrib_2025 = slcsp_2025 - ptc_2025
    contrib_2025_pct = (contrib_2025 / 50000) * 100
    print(f"\nYour contribution in 2025: ${contrib_2025:,.2f}/year ({contrib_2025_pct:.1f}% of income)")

if ptc_2026 > 0:
    contrib_2026 = slcsp_2026 - ptc_2026
    contrib_2026_pct = (contrib_2026 / 50000) * 100
    print(f"Your contribution in 2026: ${contrib_2026:,.2f}/year ({contrib_2026_pct:.1f}% of income)")
else:
    print(f"Your contribution in 2026: Full cost of insurance (no subsidy)")