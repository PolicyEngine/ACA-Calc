"""Test cliff works with employment_income."""
import sys
sys.path.insert(0, '.')

from app import calculate_ptc, get_fpl

# 60yo couple
fpl_2 = get_fpl(2)
income_at_405_fpl = int(fpl_2 * 4.05)

print(f"Testing 60yo couple at 405% FPL (${income_at_405_fpl:,})")
print(f"FPL for 2: ${fpl_2:,}, 400% FPL: ${fpl_2 * 4:,}")

ptc_baseline, slcsp = calculate_ptc(60, 60, income_at_405_fpl, [], "WV", None, use_reform=False)
ptc_reform, _ = calculate_ptc(60, 60, income_at_405_fpl, [], "WV", None, use_reform=True)

print(f"\nBaseline PTC (should be $0): ${ptc_baseline:,.0f}")
print(f"Reform PTC (should be >$0): ${ptc_reform:,.0f}")
print(f"SLCSP: ${slcsp:,.0f}")

print("\n" + "="*70)
if ptc_baseline == 0 and ptc_reform > 0:
    print("✓ CLIFF WORKS CORRECTLY!")
    print(f"  Baseline has cliff at 400% FPL (PTC = $0)")
    print(f"  Reform removes cliff (PTC = ${ptc_reform:,.0f})")
else:
    print(f"✗ CLIFF BROKEN!")
    print(f"  Expected: Baseline=$0, Reform>$0")
    print(f"  Got: Baseline=${ptc_baseline:,.0f}, Reform=${ptc_reform:,.0f}")
