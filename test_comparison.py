from policyengine_us import Simulation

print("Testing different household structures to find the discrepancy...\n")

# Test 1: Exact match to our test script
household_v1 = {
    "people": {
        "you": {
            "age": {2025: 35, 2026: 36},
            "employment_income": {2025: 50000, 2026: 50000}
        }
    },
    "families": {"your family": {"members": ["you"]}},
    "tax_units": {"your tax unit": {"members": ["you"]}},
    "households": {
        "your household": {
            "members": ["you"],
            "state_name": {2025: "NJ", 2026: "NJ"}
        }
    }
}

# Test 2: How the app might be structuring it (no marital units)
household_v2 = {
    "people": {
        "you": {
            "age": {2025: 35, 2026: 35},  # Maybe not aging?
            "employment_income": {2025: 50000, 2026: 50000}
        }
    },
    "families": {"your family": {"members": ["you"]}},
    "tax_units": {"your tax unit": {"members": ["you"]}},
    "households": {
        "your household": {
            "members": ["you"],
            "state_name": {2025: "NJ", 2026: "NJ"}
        }
    }
}

# Test 3: With county specified (though we didn't in app)
household_v3 = {
    "people": {
        "you": {
            "age": {2025: 35, 2026: 35},
            "employment_income": {2025: 50000, 2026: 50000}
        }
    },
    "families": {"your family": {"members": ["you"]}},
    "tax_units": {"your tax unit": {"members": ["you"]}},
    "households": {
        "your household": {
            "members": ["you"],
            "state_name": {2025: "NJ", 2026: "NJ"},
            "county": {2025: "ESSEX_COUNTY_NJ", 2026: "ESSEX_COUNTY_NJ"}
        }
    }
}

print("Version 1: Age 35->36, no county")
sim = Simulation(situation=household_v1)
ptc_2025 = sim.calculate("aca_ptc", map_to="household", period=2025)[0]
ptc_2026 = sim.calculate("aca_ptc", map_to="household", period=2026)[0]
print(f"  2025: ${ptc_2025:,.2f}")
print(f"  2026: ${ptc_2026:,.2f}")
print(f"  Difference: ${ptc_2025 - ptc_2026:,.2f}\n")

print("Version 2: Age stays 35, no county")
sim = Simulation(situation=household_v2)
ptc_2025 = sim.calculate("aca_ptc", map_to="household", period=2025)[0]
ptc_2026 = sim.calculate("aca_ptc", map_to="household", period=2026)[0]
print(f"  2025: ${ptc_2025:,.2f}")
print(f"  2026: ${ptc_2026:,.2f}")
print(f"  Difference: ${ptc_2025 - ptc_2026:,.2f}\n")

print("Version 3: Age 35, with Essex County")
sim = Simulation(situation=household_v3)
ptc_2025 = sim.calculate("aca_ptc", map_to="household", period=2025)[0]
ptc_2026 = sim.calculate("aca_ptc", map_to="household", period=2026)[0]
print(f"  2025: ${ptc_2025:,.2f}")
print(f"  2026: ${ptc_2026:,.2f}")
print(f"  Difference: ${ptc_2025 - ptc_2026:,.2f}\n")

# Check SLCSP differences
print("Checking SLCSP (benchmark plan costs):")
for i, (name, hh) in enumerate([("v1", household_v1), ("v2", household_v2), ("v3", household_v3)]):
    sim = Simulation(situation=hh)
    slcsp_2025 = sim.calculate("slcsp", map_to="household", period=2025)[0]
    slcsp_2026 = sim.calculate("slcsp", map_to="household", period=2026)[0]
    print(f"  {name}: 2025=${slcsp_2025:,.2f}, 2026=${slcsp_2026:,.2f}")

print("\nThe app said: 2025=$2,197, 2026=$933, Difference=$1,264")
print("Our test said: 2025=$2,197.29, 2026=$969.85, Difference=$1,227.44")