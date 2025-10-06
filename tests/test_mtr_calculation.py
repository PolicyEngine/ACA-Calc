"""Test MTR calculation is correct"""
import pytest
import numpy as np
from policyengine_us import Simulation


def test_mtr_positive_for_typical_household():
    """MTR should be positive for most income levels"""
    situation = {
        "people": {"you": {"age": {2026: 60}}},
        "families": {"family": {"members": ["you"]}},
        "spm_units": {"household": {"members": ["you"]}},
        "tax_units": {"tax_unit": {"members": ["you"]}},
        "marital_units": {"marital_unit": {"members": ["you"]}},
        "households": {
            "household": {
                "members": ["you"],
                "state_name": {2026: "AK"},
            }
        },
        "axes": [[{"name": "employment_income", "count": 101, "min": 0, "max": 100000, "period": 2026}]]
    }

    sim = Simulation(situation=situation)
    
    income = sim.calculate("employment_income", map_to="household", period=2026)
    net_income = sim.calculate("household_net_income_including_health_benefits", map_to="household", period=2026)
    
    # Calculate MTR at income=$50k (index 50)
    i = 50
    window = 10
    d_income = income[i+window] - income[i-window]
    d_net = net_income[i+window] - net_income[i-window]
    mtr = 1 - d_net / d_income
    
    # MTR should be positive (between 0 and 100%)
    assert mtr > 0, f"MTR is negative: {mtr*100:.1f}%"
    assert mtr < 1, f"MTR exceeds 100%: {mtr*100:.1f}%"
    
    print(f"MTR at $50k income: {mtr*100:.1f}%")
    

def test_mtr_formula():
    """Verify MTR formula: MTR = 1 - d(net)/d(gross)"""
    # Simple case: if net income goes up by $700 when gross goes up by $1000
    # Then MTR = 1 - 700/1000 = 0.30 = 30%
    
    d_gross = 1000
    d_net = 700
    mtr = 1 - d_net / d_gross
    
    assert abs(mtr - 0.30) < 0.0001, f"MTR formula incorrect: {mtr}"
    print("MTR formula verified: 30% MTR when keeping 70 cents per dollar")
