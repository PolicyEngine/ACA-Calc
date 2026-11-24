"""
Store the calculator's result for each of the Overview's four example
households, so picking one on the calculator page shows its result without a
request.

Each household is sent to the calculator API with exactly the request the
calculator's form sends (2027, with H.R. 1834 and 2026 current law alongside),
and the response is saved as it comes back, rounded to the cent, with the
answer at the household's earnings (/api/calculate-at-income) that its "Your
household" cards show. Writes src/data/households/calculator_examples.json,
which the calculator page loads.

Uses only the standard library: it calls a deployed API rather than running
policyengine-us. Run it against an API serving this branch's backend, after
every policyengine-us pin:

    python precompute_calculator_examples.py --api-url https://policyengine--aca-calc-api-fastapi-app.modal.run
"""

import argparse
import json
import urllib.request
from pathlib import Path

from example_households import EXAMPLES, YEAR

OUTPUT = Path(__file__).parent / "src" / "data" / "households" / "calculator_examples.json"
LIVE_API = "https://policyengine--aca-calc-api-fastapi-app.modal.run"


def form_request(household):
    """The request CalculatorForm.jsx sends for this household."""
    return {
        "year": YEAR,
        "age_head": household["age_head"],
        "age_spouse": household["age_spouse"],
        "dependent_ages": household["dependent_ages"],
        "state": household["state"],
        "county": household["county"],
        "zip_code": None,
        "show_ira": True,
        "show_prior_year": True,
    }


def rounded(value):
    """Floats to the cent, recursively."""
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, list):
        return [rounded(v) for v in value]
    if isinstance(value, dict):
        return {k: rounded(v) for k, v in value.items()}
    return value


def calculate(api_url, request, endpoint="calculate"):
    """POST the request to an endpoint, computing a fresh answer."""
    body = json.dumps({**request, "skip_cache": True}).encode()
    req = urllib.request.Request(
        f"{api_url.rstrip('/')}/api/{endpoint}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as response:
        return json.load(response), response.headers.get("X-ACA-API-Commit")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--api-url", default=LIVE_API, help="The calculator API to call")
    args = parser.parse_args()

    examples, versions, commits = [], set(), set()
    for example in EXAMPLES:
        request = form_request(example["household"])
        response, commit = calculate(args.api_url, request)
        at_income, at_income_commit = calculate(
            args.api_url, {**request, "income": example["income"]}, "calculate-at-income"
        )
        versions.update({response.get("model_version"), at_income["model_version"]})
        commits.update({commit, at_income_commit})
        examples.append({
            "key": example["key"],
            "name": example["name"],
            "description": example["description"],
            "income": example["income"],
            "request": request,
            "response": rounded(response),
            "at_income": rounded(at_income),
        })
        print(f"{example['key']}: {len(response['income'])} incomes, model {response.get('model_version')}")

    assert len(versions) == 1, f"the API answered with several model versions: {versions}"
    data = {
        "model_version": versions.pop(),
        "api_commit": commits.pop() if len(commits) == 1 else None,
        "year": YEAR,
        "examples": examples,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print(f"Saved {OUTPUT} ({OUTPUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
