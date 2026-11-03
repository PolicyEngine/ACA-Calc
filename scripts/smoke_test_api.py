"""Smoke-test the deployed ACA calculator API.

Usage: python scripts/smoke_test_api.py API_URL [--explain] [--commit SHA [--wait SECONDS]]

Checks /api/health, then both calculator endpoints: /api/calculate-stream,
which the calculator page calls, and /api/calculate, its fallback. Both
requests set skip_cache, so the deployed code computes each answer instead of
returning one from the 7-day calculation cache, and the stream check confirms
that it did. With --explain it checks /api/health and then /api/explain
instead of the calculator: it requests a fixed household's AI narrative, which
calls the Anthropic API unless the answer is already in the 7-day explanation
cache.

After a deploy, Modal can keep sending requests to the previous version's warm
containers for a while. With --commit, every response must come from that
commit's containers, which name it in an X-ACA-API-Commit header; a check that
another version answers is retried for up to --wait seconds (default 300).

Uses only the standard library, so it runs without the app's dependencies.
"""

import argparse
import json
import math
import sys
import time
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

# The calculator checks skip the cache, so they run the deployed code whatever
# the cache holds. The explain check reads it.
FRESH = {**HOUSEHOLD, "skip_cache": True}

# Set by --commit and --wait.
COMMIT = None
WAIT_SECONDS = 300


class OtherVersion(Exception):
    """A container of some other version answered."""


def check_commit(headers):
    if COMMIT is None:
        return
    commit = headers.get("X-ACA-API-Commit")
    if commit != COMMIT:
        raise OtherVersion(
            f"commit {commit}" if commit else "a version that names no commit"
        )


def build_request(url, payload):
    data = None if payload is None else json.dumps(payload).encode()
    return urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )


def call(url, payload=None, timeout=300):
    try:
        with urllib.request.urlopen(build_request(url, payload), timeout=timeout) as response:
            check_commit(response.headers)
            return json.load(response)
    except urllib.error.HTTPError as error:
        check_commit(error.headers)
        sys.exit(f"FAIL {url} returned {error.code}: {error.read().decode()[:500]}")


def stream_events(url, payload, timeout=300):
    """Yield the server-sent events that a POST to url returns."""
    try:
        with urllib.request.urlopen(build_request(url, payload), timeout=timeout) as response:
            check_commit(response.headers)
            for line in response:
                if line.startswith(b"data: "):
                    yield json.loads(line[len(b"data: "):])
    except urllib.error.HTTPError as error:
        check_commit(error.headers)
        sys.exit(f"FAIL {url} returned {error.code}: {error.read().decode()[:500]}")


def from_this_deploy(check, base):
    """Run a check, again while another version's containers answer it."""
    deadline = time.monotonic() + WAIT_SECONDS
    while True:
        try:
            return check(base)
        except OtherVersion as other:
            if time.monotonic() > deadline:
                sys.exit(
                    f"FAIL {check.__name__}: {other} still answered after "
                    f"{WAIT_SECONDS} s, not commit {COMMIT}"
                )
            print(f"waiting: {other} answered {check.__name__}", flush=True)
            time.sleep(5)


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


def check_calculate_stream(base, household=FRESH):
    # The calculator page's endpoint. An API that predates skip_cache ignores
    # it, so a cached answer means the deploy didn't take.
    computed, result = read_stream(
        stream_events(f"{base}/api/calculate-stream", household)
    )
    if not computed:
        sys.exit(
            "FAIL /api/calculate-stream answered from the cache although the "
            "request skipped it, so the deployed API doesn't honor skip_cache"
        )
    check_result("/api/calculate-stream", result)


def check_calculate(base):
    # The page's fallback when the stream fails. Its response doesn't say
    # whether it came from the cache, so this relies on the request skipping it.
    check_result("/api/calculate", call(f"{base}/api/calculate", FRESH))


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
    global COMMIT, WAIT_SECONDS
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("api_url")
    parser.add_argument(
        "--explain",
        action="store_true",
        help="check AI explanations instead of the calculator",
    )
    parser.add_argument(
        "--commit", help="accept answers only from containers of this commit"
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=WAIT_SECONDS,
        help="seconds to wait for the commit's containers to answer each check",
    )
    args = parser.parse_args()
    COMMIT, WAIT_SECONDS = args.commit, args.wait
    base = args.api_url.rstrip("/")
    if args.explain:
        checks = [check_health, check_explain]
    else:
        checks = [check_health, check_calculate_stream, check_calculate]
    for check in checks:
        from_this_deploy(check, base)


if __name__ == "__main__":
    main()
