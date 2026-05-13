"""Build state-level context and modeled local backfills for SBM states."""

from __future__ import annotations

import argparse
import csv
import json
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from aca_calc.congressional_district_ingest import (
        build_district_enrollment_records_from_population_distribution,
    )
except ModuleNotFoundError:  # pragma: no cover - supports direct script usage
    from congressional_district_ingest import (
        build_district_enrollment_records_from_population_distribution,
    )


COUNT_FIELDS = (
    "marketplace_plan_selections",
    "new_consumers",
    "returning_consumers",
    "consumers_with_aptc_or_csr",
    "aptc_consumers",
    "consumers_premium_after_aptc_lte_10",
)

AVERAGE_FIELDS = (
    "average_premium",
    "average_premium_after_aptc",
    "average_aptc",
    "aptc_consumer_average_paid_premium",
)

CMS_2026_OEP_PUFS_URL = (
    "https://www.cms.gov/data-research/statistics-trends-reports/"
    "marketplace-products/2026-marketplace-open-enrollment-period-public-use-files"
)
CMS_STATE_PUF_URL = (
    "https://www.cms.gov/files/zip/"
    "2026-oep-state-level-public-use-file.zip"
)
PE_BLOCK_DISTRIBUTION_URL = (
    "https://github.com/PolicyEngine/policyengine-us-data/blob/master/"
    "policyengine_us_data/storage/calibration_targets/"
    "make_block_cd_distributions.py"
)

STATE_FIPS_TO_ABBR = {
    "01": "AL",
    "02": "AK",
    "04": "AZ",
    "05": "AR",
    "06": "CA",
    "08": "CO",
    "09": "CT",
    "10": "DE",
    "11": "DC",
    "12": "FL",
    "13": "GA",
    "15": "HI",
    "16": "ID",
    "17": "IL",
    "18": "IN",
    "19": "IA",
    "20": "KS",
    "21": "KY",
    "22": "LA",
    "23": "ME",
    "24": "MD",
    "25": "MA",
    "26": "MI",
    "27": "MN",
    "28": "MS",
    "29": "MO",
    "30": "MT",
    "31": "NE",
    "32": "NV",
    "33": "NH",
    "34": "NJ",
    "35": "NM",
    "36": "NY",
    "37": "NC",
    "38": "ND",
    "39": "OH",
    "40": "OK",
    "41": "OR",
    "42": "PA",
    "44": "RI",
    "45": "SC",
    "46": "SD",
    "47": "TN",
    "48": "TX",
    "49": "UT",
    "50": "VT",
    "51": "VA",
    "53": "WA",
    "54": "WV",
    "55": "WI",
    "56": "WY",
}


def _number(value: Any) -> int | None:
    if value is None:
        return None

    cleaned = str(value).strip().replace(",", "").replace("$", "")
    if cleaned in {"", "+", "*", "NR", "N/A"}:
        return None

    return int(round(float(cleaned)))


def _allocate(value: int | None, share: float) -> int | None:
    if value is None:
        return None
    return round(value * share)


def _district_label(state: str, district: str) -> str:
    if district in {"00", "98"}:
        return f"{state} at-large"
    return f"{state}-{int(district):02d}"


def load_state_records_from_cms_puf(
    state_puf_zip: str | Path,
    platforms: dict[str, Any],
) -> list[dict[str, Any]]:
    """Load observed state-level records from the CMS 2026 state OEP PUF."""
    with zipfile.ZipFile(state_puf_zip) as archive:
        csv_name = next(
            name for name in archive.namelist() if name.lower().endswith(".csv")
        )
        rows = list(
            csv.DictReader(
                archive.read(csv_name).decode("utf-8-sig").splitlines()
            )
        )

    platform_by_state = {
        state: "HealthCare.gov" for state in platforms["healthcare_gov_states"]
    } | {
        state: "State-based marketplace"
        for state in platforms["state_based_marketplace_states"]
    }

    records = []
    for row in rows:
        state = row["State_Abrvtn"].strip()
        if state not in platform_by_state:
            continue

        records.append(
            {
                "state": state,
                "marketplace_platform": platform_by_state.get(
                    state,
                    row.get("Pltfrm"),
                ),
                "source_level": "cms_state_puf",
                "marketplace_plan_selections": _number(row.get("Cnsmr")),
                "new_consumers": _number(row.get("New_Cnsmr")),
                "returning_consumers": _number(row.get("Tot_Renrl")),
                "consumers_with_aptc_or_csr": _number(
                    row.get("Cnsmr_Wth_APTC_CSR")
                ),
                "aptc_consumers": _number(row.get("APTC_Cnsmr")),
                "average_premium": _number(row.get("Avg_Prm")),
                "average_premium_after_aptc": _number(
                    row.get("Avg_Prm_Aftr_APTC")
                ),
                "average_aptc": _number(row.get("APTC_Cnsmr_Avg_APTC")),
                "aptc_consumer_average_paid_premium": _number(
                    row.get("APTC_Cnsmr_Avg_Prm_Aftr_APTC")
                ),
                "consumers_premium_after_aptc_lte_10": _number(
                    row.get("Cnsmr_Prm_Aftr_APTC_LTEQ10")
                ),
            }
        )

    return sorted(records, key=lambda record: record["state"])


def load_counties(county_fips_file: str | Path) -> dict[str, dict[str, str]]:
    with Path(county_fips_file).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="|")
        return {
            row["STATEFP"] + row["COUNTYFP"]: {
                "state": row["STATE"],
                "county": row["COUNTYNAME"],
                "county_fips": row["STATEFP"] + row["COUNTYFP"],
            }
            for row in reader
        }


def load_county_population_shares(
    county_distribution_path: str | Path,
) -> dict[str, dict[str, float]]:
    """Infer county population shares from PolicyEngine CD-county shares."""
    state_cd_count: dict[str, set[int]] = defaultdict(set)
    raw_shares: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    with Path(county_distribution_path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cd_geoid = int(row["cd_geoid"])
            county_fips = row["county_fips"]
            state = STATE_FIPS_TO_ABBR[county_fips[:2]]
            state_cd_count[state].add(cd_geoid)
            raw_shares[state][county_fips] += float(row["probability"])

    county_shares = {}
    for state, counties in raw_shares.items():
        district_count = len(state_cd_count[state])
        county_shares[state] = {
            county_fips: share / district_count
            for county_fips, share in counties.items()
        }

    return county_shares


def build_modeled_county_records(
    state_records: list[dict[str, Any]],
    county_shares: dict[str, dict[str, float]],
    counties: dict[str, dict[str, str]],
    sbm_states: set[str],
) -> list[dict[str, Any]]:
    records = []
    states = {record["state"]: record for record in state_records}

    for state in sorted(sbm_states):
        state_record = states[state]
        for county_fips, share in sorted(county_shares[state].items()):
            county = counties[county_fips]
            record = {
                "state": state,
                "county": county["county"],
                "county_fips": county_fips,
                "source_level": "policyengine_modeled_county_backfill",
                "allocation_basis": (
                    "CMS state-level OEP PUF total allocated by county "
                    "population shares inferred from PolicyEngine US Data's "
                    "119th congressional district block-population distribution."
                ),
                "modeled_share": share,
            }
            for field in COUNT_FIELDS:
                record[field] = _allocate(state_record.get(field), share)
            for field in AVERAGE_FIELDS:
                record[field] = state_record.get(field)
            records.append(record)

    return records


def build_modeled_district_records(
    state_records: list[dict[str, Any]],
    modeled_county_records: list[dict[str, Any]],
    county_distribution_path: str | Path,
    district_geography: dict[str, Any],
    sbm_states: set[str],
) -> list[dict[str, Any]]:
    states = {record["state"]: record for record in state_records}
    feature_by_geoid = {
        feature["properties"]["geoid"]: feature
        for feature in district_geography["features"]
    }
    raw_records = build_district_enrollment_records_from_population_distribution(
        {"records": modeled_county_records},
        county_distribution_path,
    )

    records = []
    for record in raw_records:
        state = record["state"]
        if state not in sbm_states:
            continue

        state_record = states[state]
        feature = feature_by_geoid[record["district_geoid"]]
        district = feature["properties"]["district"]
        state_plan_selections = state_record.get("marketplace_plan_selections")
        modeled_share = (
            record["marketplace_plan_selections"] / state_plan_selections
            if state_plan_selections
            else None
        )
        records.append(
            {
                **record,
                "district": district,
                "district_label": _district_label(state, district),
                "district_name": feature["properties"]["namelsad"],
                "source_level": "policyengine_modeled_state_backfill",
                "allocation_basis": (
                    "CMS state-level OEP PUF total allocated to counties and "
                    "119th congressional districts using PolicyEngine US "
                    "Data's block-population county-CD distribution."
                ),
                "modeled_share": modeled_share,
            }
        )

    return sorted(records, key=lambda record: record["district_geoid"])


def write_state_context(
    records: list[dict[str, Any]],
    output_path: str | Path,
) -> None:
    output = {
        "year": 2026,
        "source": "CMS 2026 Marketplace Open Enrollment State-Level Public Use File",
        "source_url": CMS_STATE_PUF_URL,
        "records": records,
    }
    Path(output_path).write_text(json.dumps(output, indent=2) + "\n")


def write_modeled_county_context(
    records: list[dict[str, Any]],
    output_path: str | Path,
) -> None:
    output = {
        "year": 2026,
        "source": (
            "CMS 2026 Marketplace Open Enrollment State-Level Public Use File "
            "and PolicyEngine US Data block-population geography"
        ),
        "source_url": CMS_STATE_PUF_URL,
        "allocation_method": (
            "State-based marketplace county rows are modeled backfills. "
            "Observed CMS state totals are allocated with county population "
            "shares inferred from PolicyEngine US Data's 119th congressional "
            "district block-population distribution."
        ),
        "records": records,
    }
    Path(output_path).write_text(json.dumps(output, indent=2) + "\n")


def merge_district_context(
    observed_district_path: str | Path,
    modeled_records: list[dict[str, Any]],
    output_path: str | Path,
    sbm_states: set[str],
) -> None:
    with Path(observed_district_path).open() as f:
        observed = json.load(f)

    observed_records = [
        {
            **record,
            "source_level": record.get(
                "source_level",
                "cms_county_puf_policyengine_population_allocation",
            ),
        }
        for record in observed["records"]
        if record["state"] not in sbm_states
    ]

    observed["source"] = (
        "CMS 2026 Marketplace Open Enrollment PUFs and PolicyEngine US Data "
        "block-population geography"
    )
    observed["source_url"] = CMS_2026_OEP_PUFS_URL
    observed["source_urls"] = [
        observed["source_url"],
        PE_BLOCK_DISTRIBUTION_URL,
    ]
    observed["allocation_method"] = (
        "HealthCare.gov-platform districts use CMS county-level PUF rows "
        "allocated with PolicyEngine population shares. State-based "
        "marketplace districts use observed CMS state-level PUF totals with "
        "a PolicyEngine-modeled local backfill."
    )
    observed["records"] = sorted(
        observed_records + modeled_records,
        key=lambda record: (record["state"], record["district"]),
    )
    Path(output_path).write_text(json.dumps(observed, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-puf-zip", required=True)
    parser.add_argument("--platforms", required=True)
    parser.add_argument("--county-fips-file", required=True)
    parser.add_argument("--county-distribution", required=True)
    parser.add_argument("--district-geography", required=True)
    parser.add_argument("--observed-district-context", required=True)
    parser.add_argument("--state-output", required=True)
    parser.add_argument("--modeled-county-output", required=True)
    parser.add_argument("--district-output", required=True)
    args = parser.parse_args()

    platforms = json.loads(Path(args.platforms).read_text())
    sbm_states = set(platforms["state_based_marketplace_states"])
    state_records = load_state_records_from_cms_puf(args.state_puf_zip, platforms)
    counties = load_counties(args.county_fips_file)
    county_shares = load_county_population_shares(args.county_distribution)
    district_geography = json.loads(Path(args.district_geography).read_text())

    modeled_counties = build_modeled_county_records(
        state_records,
        county_shares,
        counties,
        sbm_states,
    )
    modeled_districts = build_modeled_district_records(
        state_records,
        modeled_counties,
        args.county_distribution,
        district_geography,
        sbm_states,
    )

    write_state_context(state_records, args.state_output)
    write_modeled_county_context(modeled_counties, args.modeled_county_output)
    merge_district_context(
        args.observed_district_context,
        modeled_districts,
        args.district_output,
        sbm_states,
    )


if __name__ == "__main__":
    main()
