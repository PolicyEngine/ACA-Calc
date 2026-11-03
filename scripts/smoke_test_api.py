"""Smoke-test the deployed ACA calculator API.

Usage: python scripts/smoke_test_api.py API_URL [--explain]

Checks /api/health, then both calculator endpoints: /api/calculate-stream,
which the calculator page calls, and /api/calculate, its fallback. Both vary
the household so the deployed code computes the answer instead of returning
one from the 7-day calculation cache, and the stream check confirms that it
did. With --explain it also
requests a fixed household's AI narrative from /api/explain, which calls the
Anthropic API unless the answer is already in the 7-day explanation cache.
Uses only the standard library, so it runs without the app's dependencies.
"""

import argparse
import json
import math
import random
import sys
import urllib.error
import urllib.request

# The IRA-extension scenario is off because it fails on the pinned
# policyengine-us, which restructured gov.aca.required_contribution_percentage.
# Checking it would roll back every deploy until the reform is fixed.
HOUSEHOLD = {
    "age_head": 35,
    "state": "PA",
    "county": "Lebanon County",
    "show_ira": False,
    "show_700fpl": True,
}

# The calculation cache is keyed on the household, so the calculator checks
# vary the head's age. HOUSEHOLD's own age is left out because the explain
# check keeps it in the cache.
AGES = [age for age in range(21, 65) if age != HOUSEHOLD["age_head"]]
STREAM_TRIES = 10


def build_request(url, payload):
    data = None if payload is None else json.dumps(payload).encode()
    return urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )


def call(url, payload=None, timeout=300):
    try:
        with urllib.request.urlopen(build_request(url, payload), timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        sys.exit(f"FAIL {url} returned {error.code}: {error.read().decode()[:500]}")


def stream_events(url, payload, timeout=300):
    """Yield the server-sent events that a POST to url returns."""
    try:
        with urllib.request.urlopen(build_request(url, payload), timeout=timeout) as response:
            for line in response:
                if line.startswith(b"data: "):
                    yield json.loads(line[len(b"data: "):])
    except urllib.error.HTTPError as error:
        sys.exit(f"FAIL {url} returned {error.code}: {error.read().decode()[:500]}")


def read_stream(events):
    """Return a calculate-stream answer and whether the server computed it.

    The endpoint reports errors as events in an HTTP 200 response, so the
    status alone doesn't show success. A cached answer starts with a "cached"
    event.
    """
    computed = None
    for event in events:
        if computed is None:
            computed = event.get("step") != "cached"
        if event.get("step") == "error":
            sys.exit(f"FAIL /api/calculate-stream sent an error: {event.get('error')}")
        if event.get("step") == "complete":
            return computed, event["result"]
    sys.exit("FAIL /api/calculate-stream ended without a result")


def check_result(label, result):
    points = len(result["income"])
    assert points > 1, f"{label}: income has {points} points"
    for name, values in result.items():
        if isinstance(values, list):
            assert len(values) == points, f"{label}: {name} has {len(values)} points"
            assert all(math.isfinite(v) and v >= 0 for v in values), (
                f"{label}: {name} has a negative or non-finite value"
            )
    assert result["fpl"] > 0 and result["slcsp"] > 0, (result["fpl"], result["slcsp"])
    assert max(result["ptc_baseline"]) > 0, f"{label}: baseline PTC is zero at every income"
    assert max(result["ptc_700fpl"]) > 0, f"{label}: 700% FPL PTC is zero at every income"
    print(
        f"ok {label}: {points} points, FPL {result['fpl']:,.0f}, "
        f"SLCSP {result['slcsp']:,.0f}, "
        f"max baseline PTC {max(result['ptc_baseline']):,.0f}"
    )


def check_health(base):
    result = call(f"{base}/api/health")
    assert result == {"status": "healthy"}, result
    print("ok /api/health")


def check_calculate_stream(base, ages):
    # The calculator page's endpoint. Moves to the next age while answers come
    # from the cache, until the deployed code computes one.
    for age in ages:
        household = {**HOUSEHOLD, "age_head": age}
        computed, result = read_stream(
            stream_events(f"{base}/api/calculate-stream", household)
        )
        if computed:
            check_result(f"/api/calculate-stream (age {age})", result)
            return
    sys.exit(
        f"FAIL /api/calculate-stream: the answers for ages {list(ages)} all came "
        "from the cache, so this deploy's code never ran"
    )


def check_calculate(base, age):
    # The page's fallback when the stream fails. Its response doesn't say
    # whether it came from the cache, so it gets an age the stream check didn't
    # try.
    result = call(f"{base}/api/calculate", {**HOUSEHOLD, "age_head": age})
    check_result(f"/api/calculate (age {age})", result)


def check_explain(base):
    # A fixed household, so after the first deploy the answer usually comes
    # from the explanation cache rather than a new Anthropic API call.
    calculation = call(f"{base}/api/calculate", HOUSEHOLD)
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
        "show_ira": False,
        "show_700fpl": True,
        "sample_income": sample,
        "ptc_baseline_at_sample": calculation["ptc_baseline"][nearest],
        "ptc_700fpl_at_sample": calculation["ptc_700fpl"][nearest],
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
    ages = random.sample(AGES, len(AGES))
    check_health(base)
    check_calculate_stream(base, ages[:STREAM_TRIES])
    check_calculate(base, ages[-1])
    if args.explain:
        check_explain(base)


if __name__ == "__main__":
    main()
