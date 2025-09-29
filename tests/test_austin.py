from policyengine_us import Simulation

# Austin, TX couple - 25 and 28 years old, $60k income
household = {
    "people": {
        "you": {
            "age": {2025: 25, 2026: 25},
            "employment_income": {2025: 30000, 2026: 30000}  # Split income
        },
        "your partner": {
            "age": {2025: 28, 2026: 28},
            "employment_income": {2025: 30000, 2026: 30000}  # Split income
        }
    },
    "families": {
        "your family": {
            "members": ["you", "your partner"]
        }
    },
    "tax_units": {
        "your tax unit": {
            "members": ["you", "your partner"]
        }
    },
    "households": {
        "your household": {
            "members": ["you", "your partner"],
            "state_name": {2025: "TX", 2026: "TX"}
        }
    },
    "marital_units": {
        "your marital unit": {
            "members": ["you", "your partner"]
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
fpl_2026_couple = 21130  # Couple FPL
fpl_pct = (60000 / fpl_2026_couple) * 100

print("="*60)
print("AUSTIN, TEXAS")
print("Married couple, ages 25 & 28, $60,000 household income")
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
    print(f"  This couple will pay ${difference/12:,.2f} more per month for health insurance")
elif difference < 0:
    print(f"  Gain: ${abs(difference):,.2f}/year (${abs(difference)/12:,.2f}/month)")
else:
    print(f"  No change")

# Calculate what percentage of income they pay
if slcsp_2025 > 0 and ptc_2025 >= 0:
    contrib_2025 = slcsp_2025 - ptc_2025
    contrib_2025_pct = (contrib_2025 / 60000) * 100
    print(f"\nYour contribution in 2025: ${contrib_2025:,.2f}/year ({contrib_2025_pct:.1f}% of income)")

if slcsp_2026 > 0 and ptc_2026 >= 0:
    contrib_2026 = slcsp_2026 - ptc_2026
    contrib_2026_pct = (contrib_2026 / 60000) * 100
    print(f"Your contribution in 2026: ${contrib_2026:,.2f}/year ({contrib_2026_pct:.1f}% of income)")

# Compare to notebook example at 300% FPL ($63,450)
print(f"\n" + "="*60)
print("Comparison to notebook Texas couple at 300% FPL ($63,450):")
print("The notebook showed: baseline=$4,062, reform=$6,283")
print("(Note: notebook tested extending IRA vs letting expire)")
print("="*60)