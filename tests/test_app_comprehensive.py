"""
Comprehensive verification test for the fixed app.py
Tests all critical scenarios to ensure calculations match notebook values
"""
import sys
sys.path.insert(0, '.')

# Import the fixed calculate_ptc function from app.py
from app import calculate_ptc

print("="*70)
print("COMPREHENSIVE APP VERIFICATION TEST")
print("="*70)

# Test scenarios from notebook
test_cases = [
    {
        "name": "Texas couple at 300% FPL ($63,450)",
        "age_head": 25,
        "age_spouse": 28,
        "income": 63450,
        "dependent_ages": [],
        "state": "TX",
        "county": None,
        "expected_baseline": 4062,
        "expected_reform": 6283,
    },
    {
        "name": "Texas couple at 400% FPL ($84,600) - THE CLIFF",
        "age_head": 25,
        "age_spouse": 28,
        "income": 84600,
        "dependent_ages": [],
        "state": "TX",
        "county": None,
        "expected_baseline": 0,
        "expected_reform": 2899,
    },
    {
        "name": "Texas couple at 138% FPL ($29,187)",
        "age_head": 25,
        "age_spouse": 28,
        "income": 29187,
        "dependent_ages": [],
        "state": "TX",
        "county": None,
        "expected_baseline": 9129,
        "expected_reform": 10090,
    },
    {
        "name": "NY family (30+30+3yo) at 300% FPL ($79,950)",
        "age_head": 30,
        "age_spouse": 30,
        "income": 79950,
        "dependent_ages": [3],
        "state": "NY",
        "county": None,
        "expected_baseline": 13848,
        "expected_reform": 16646,
    },
    {
        "name": "NY family at 405% FPL ($107,933) - Above cliff",
        "age_head": 30,
        "age_spouse": 30,
        "income": 107933,
        "dependent_ages": [3],
        "state": "NY",
        "county": None,
        "expected_baseline": 0,
        "expected_reform": 12269,
    },
]

passed = 0
failed = 0
tolerance = 100  # Allow $100 difference due to rounding

for i, test in enumerate(test_cases, 1):
    print(f"\n{'='*70}")
    print(f"TEST {i}: {test['name']}")
    print(f"{'='*70}")

    # Calculate baseline
    ptc_baseline, slcsp = calculate_ptc(
        test['age_head'],
        test['age_spouse'],
        test['income'],
        test['dependent_ages'],
        test['state'],
        test['county'],
        use_reform=False
    )

    # Calculate reform
    ptc_reform, _ = calculate_ptc(
        test['age_head'],
        test['age_spouse'],
        test['income'],
        test['dependent_ages'],
        test['state'],
        test['county'],
        use_reform=True
    )

    # Check results
    baseline_diff = abs(ptc_baseline - test['expected_baseline'])
    reform_diff = abs(ptc_reform - test['expected_reform'])

    baseline_ok = baseline_diff < tolerance
    reform_ok = reform_diff < tolerance

    print(f"\nBaseline PTC:")
    print(f"  Expected: ${test['expected_baseline']:,.0f}")
    print(f"  Got:      ${ptc_baseline:,.0f}")
    print(f"  Diff:     ${baseline_diff:,.0f}")
    print(f"  Status:   {'✓ PASS' if baseline_ok else '✗ FAIL'}")

    print(f"\nReform PTC:")
    print(f"  Expected: ${test['expected_reform']:,.0f}")
    print(f"  Got:      ${ptc_reform:,.0f}")
    print(f"  Diff:     ${reform_diff:,.0f}")
    print(f"  Status:   {'✓ PASS' if reform_ok else '✗ FAIL'}")

    print(f"\nSLCSP: ${slcsp:,.0f}/year")
    print(f"Difference (Reform - Baseline): ${ptc_reform - ptc_baseline:,.0f}")

    if baseline_ok and reform_ok:
        print(f"\n✓ TEST {i} PASSED")
        passed += 1
    else:
        print(f"\n✗ TEST {i} FAILED")
        failed += 1

# Edge case tests
print(f"\n{'='*70}")
print("EDGE CASE TESTS")
print(f"{'='*70}")

# Test with multiple children
print(f"\n--- Test: Family with 3 children ---")
ptc_base, slcsp = calculate_ptc(35, 35, 80000, [5, 8, 12], "TX", None, use_reform=False)
ptc_ref, _ = calculate_ptc(35, 35, 80000, [5, 8, 12], "TX", None, use_reform=True)
print(f"Baseline: ${ptc_base:,.0f}, Reform: ${ptc_ref:,.0f}, SLCSP: ${slcsp:,.0f}")
if ptc_ref > ptc_base and slcsp > 0:
    print("✓ PASS - Reform gives higher benefit and SLCSP exists")
    passed += 1
else:
    print("✗ FAIL - Something wrong with multi-child calculation")
    failed += 1

# Test single person
print(f"\n--- Test: Single person at 250% FPL ---")
ptc_base, slcsp = calculate_ptc(40, None, 40000, [], "TX", None, use_reform=False)
ptc_ref, _ = calculate_ptc(40, None, 40000, [], "TX", None, use_reform=True)
print(f"Baseline: ${ptc_base:,.0f}, Reform: ${ptc_ref:,.0f}, SLCSP: ${slcsp:,.0f}")
if ptc_ref >= ptc_base and slcsp > 0:
    print("✓ PASS - Single person calculation works")
    passed += 1
else:
    print("✗ FAIL - Single person calculation issue")
    failed += 1

# Summary
print(f"\n{'='*70}")
print("FINAL RESULTS")
print(f"{'='*70}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Total:  {passed + failed}")

if failed == 0:
    print("\n✓✓✓ ALL TESTS PASSED! ✓✓✓")
    print("The app is working correctly!")
else:
    print(f"\n✗ {failed} test(s) failed. Review issues above.")

sys.exit(0 if failed == 0 else 1)