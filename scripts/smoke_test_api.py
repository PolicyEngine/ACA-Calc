"""Smoke-test the deployed ACA calculator API.

Usage: python scripts/smoke_test_api.py API_URL [--explain]

Checks /api/health and /api/calculate for one household. With --explain it
also requests that household's AI narrative from /api/explain, which calls the
Anthropic API unless the answer is already in the 7-day explanation cache.
Uses only the standard library, so it runs without the app's dependencies.
"""

import argparse
import json
import math
import sys
import urllib.error
import urllib.request

HOUSEHOLD = {"age_head": 35, "state": "PA", "county": "Lebanon County"}
POINTS = 10_001
SERIES = ["income", "ptc_baseline", "ptc_ira", "medicaid", "chip"]


def call(url, payload=None, timeout=300):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        sys.exit(f"FAIL {url} returned {error.code}: {error.read().decode()[:500]}")


def check_health(base):
    result = call(f"{base}/api/health")
    assert result == {"status": "healthy"}, result
    print("ok /api/health")


def check_calculate(base):
    result = call(f"{base}/api/calculate", HOUSEHOLD)
    for name in SERIES:
        values = result[name]
        assert len(values) == POINTS, f"{name} has {len(values)} points"
        assert all(math.isfinite(v) and v >= 0 for v in values), (
            f"{name} has a negative or non-finite value"
        )
    assert result["fpl"] > 0 and result["slcsp"] > 0, (result["fpl"], result["slcsp"])
    assert max(result["ptc_baseline"]) > 0, "baseline PTC is zero at every income"
    print(
        f"ok /api/calculate: FPL {result['fpl']:,.0f}, SLCSP {result['slcsp']:,.0f}, "
        f"max baseline PTC {max(result['ptc_baseline']):,.0f}"
    )
    return result


def check_explain(base, calculation):
    # Build the request the way the calculator page does (Calculator.jsx).
    fpl = calculation["fpl"]
    sample = fpl * 3
    income = calculation["income"]
    nearest = min(range(len(income)), key=lambda i: abs(income[i] - sample))
    request = {
        **HOUSEHOLD,
        "is_expansion_state": True,
        "fpl": fpl,
        "slcsp": calculation["slcsp"],
        "fpl_400_income": fpl * 4,
        "fpl_700_income": fpl * 7,
        "medicaid_adult_threshold_pct": 138,
        "medicaid_child_threshold_pct": 162,
        "chip_threshold_pct": 0,
        "show_ira": True,
        "show_700fpl": False,
        "sample_income": sample,
        "ptc_baseline_at_sample": calculation["ptc_baseline"][nearest],
        "ptc_ira_at_sample": calculation["ptc_ira"][nearest],
    }
    result = call(f"{base}/api/explain", request, timeout=600)
    sections = result["sections"]
    assert sections, "no sections"
    for section in sections:
        for field in ("id", "title", "content", "chartState"):
            assert section[field].strip(), f"section {section.get('id')} has no {field}"
    assert result["household_description"].strip(), "no household description"
    print(
        f"ok /api/explain: {len(sections)} sections for "
        f"{result['household_description']!r}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("api_url")
    parser.add_argument("--explain", action="store_true")
    args = parser.parse_args()
    base = args.api_url.rstrip("/")
    check_health(base)
    calculation = check_calculate(base)
    if args.explain:
        check_explain(base, calculation)


if __name__ == "__main__":
    main()
