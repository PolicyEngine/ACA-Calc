"""Build compact Marketplace enrollment context from CMS OEP PUF files."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


DEFAULT_SOURCE = (
    "CMS 2026 Marketplace Open Enrollment Period County-Level and ZIP-Level "
    "Public Use Files"
)
DEFAULT_SOURCE_URL = (
    "https://www.cms.gov/data-research/statistics-trends-reports/"
    "marketplace-products/2026-marketplace-open-enrollment-period-public-use-files"
)
SUPPRESSED_VALUES = {"", "*", "+", "total"}


def parse_cms_number(value: str | int | float | None) -> int | float | None:
    """Parse CMS PUF counts/currency while preserving suppressed values."""
    if value is None:
        return None
    if isinstance(value, int | float):
        return value

    text = value.strip().strip('"')
    if text.casefold() in SUPPRESSED_VALUES:
        return None

    cleaned = text.replace("$", "").replace(",", "").strip()
    if cleaned.casefold() in SUPPRESSED_VALUES:
        return None

    try:
        parsed = float(cleaned)
    except ValueError:
        return None

    return int(parsed) if parsed.is_integer() else parsed


def _int_value(value: str | int | float | None) -> int | None:
    parsed = parse_cms_number(value)
    return int(parsed) if parsed is not None else None


def _float_value(value: str | int | float | None) -> float | None:
    parsed = parse_cms_number(value)
    return float(parsed) if parsed is not None else None


def transform_county_row(
    row: dict[str, str],
    county_name: str,
    zip_examples: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Transform a CMS County-Level PUF row into the app fixture schema."""
    record = {
        "state": row["State_Abrvtn"].strip().upper(),
        "county": county_name,
        "county_fips": row["County_FIPS_Cd"].strip(),
        "marketplace_plan_selections": _int_value(row.get("Cnsmr")),
        "new_consumers": _int_value(row.get("New_Cnsmr")),
        "returning_consumers": _int_value(row.get("Tot_Renrl")),
        "consumers_with_aptc_or_csr": _int_value(
            row.get("Cnsmr_Wth_APTC_CSR")
        ),
        "aptc_consumers": _int_value(row.get("APTC_Cnsmr")),
        "average_premium": _float_value(row.get("Avg_Prm")),
        "average_premium_after_aptc": _float_value(
            row.get("Avg_Prm_Aftr_APTC")
        ),
        "average_aptc": _float_value(row.get("APTC_Cnsmr_Avg_APTC")),
        "consumers_premium_after_aptc_lte_10": _int_value(
            row.get("Cnsmr_Prm_Aftr_APTC_LTEQ10")
        ),
    }
    if zip_examples:
        record["zip_examples"] = zip_examples
    return record


def transform_zip_row(row: dict[str, str]) -> dict[str, Any]:
    """Transform a CMS ZIP-Level PUF row into a compact example row."""
    return {
        "zip": row["zip"].strip(),
        "marketplace_plan_selections": _int_value(row.get("Cnsmr")),
        "aptc_consumers": _int_value(row.get("APTC_Cnsmr")),
        "average_aptc": _float_value(row.get("APTC_Cnsmr_Avg_APTC")),
    }


def load_zip_examples(
    zip_puf_path: str | Path,
    zip_codes: list[str],
) -> list[dict[str, Any]]:
    """Return selected ZIP rows from a CMS ZIP-Level PUF CSV."""
    wanted = set(zip_codes)
    examples: list[dict[str, Any]] = []

    with Path(zip_puf_path).open(newline="") as f:
        for row in csv.DictReader(f):
            if row["zip"].strip() in wanted:
                examples.append(transform_zip_row(row))

    return sorted(examples, key=lambda record: record["zip"])


def load_county_fips_mapping(path: str | Path) -> dict[str, str]:
    """Load a county FIPS to county name mapping.

    Supports the Census national county code file shape
    (STATE, STATEFP, COUNTYFP, COUNTYNAME, CLASSFP) and simple files with
    county_fips/county_name columns.
    """
    mapping: dict[str, str] = {}

    with Path(path).open(newline="") as f:
        rows = list(csv.reader(f))

    if not rows:
        return mapping

    header = rows[0]
    if {"county_fips", "county_name"}.issubset(header):
        for values in rows[1:]:
            row = dict(zip(header, values))
            mapping[row["county_fips"].strip()] = row["county_name"].strip()
        return mapping

    census_header = ["STATE", "STATEFP", "COUNTYFP", "COUNTYNAME", "CLASSFP"]
    data_rows = rows[1:] if header[:5] == census_header else rows
    for row in data_rows:
        if len(row) >= 4:
            mapping[f"{row[1].strip()}{row[2].strip()}"] = row[3].strip()

    return mapping


def build_enrollment_context_fixture(
    county_puf_path: str | Path,
    county_fips_to_name: dict[str, str],
    *,
    zip_puf_path: str | Path | None = None,
    zip_examples_by_county_fips: dict[str, list[str]] | None = None,
    year: int = 2026,
    source: str = DEFAULT_SOURCE,
    source_url: str = DEFAULT_SOURCE_URL,
) -> dict[str, Any]:
    """Build a compact fixture from selected CMS County/ZIP PUF rows."""
    zip_examples_by_county_fips = zip_examples_by_county_fips or {}
    records: list[dict[str, Any]] = []

    with Path(county_puf_path).open(newline="") as f:
        for row in csv.DictReader(f):
            county_fips = row.get("County_FIPS_Cd", "").strip()
            if county_fips not in county_fips_to_name:
                continue

            zip_examples = None
            if zip_puf_path and county_fips in zip_examples_by_county_fips:
                zip_examples = load_zip_examples(
                    zip_puf_path,
                    zip_examples_by_county_fips[county_fips],
                )

            records.append(
                transform_county_row(
                    row,
                    county_fips_to_name[county_fips],
                    zip_examples=zip_examples,
                )
            )

    return {
        "year": year,
        "source": source,
        "source_url": source_url,
        "records": sorted(
            records,
            key=lambda record: (record["state"], record["county"]),
        ),
    }


def write_enrollment_context_fixture(
    output_path: str | Path,
    fixture: dict[str, Any],
) -> None:
    """Write a compact enrollment context fixture."""
    with Path(output_path).open("w") as f:
        json.dump(fixture, f, indent=2)
        f.write("\n")


def _parse_county_mapping(values: list[str]) -> dict[str, str]:
    return dict(value.split("=", 1) for value in values)


def _parse_zip_mapping(values: list[str]) -> dict[str, list[str]]:
    return {
        fips: [zip_code.strip() for zip_code in zip_codes.split(",")]
        for fips, zip_codes in (value.split("=", 1) for value in values)
    }


def main(argv: list[str] | None = None) -> None:
    """CLI for creating a compact fixture from selected PUF rows."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--county-puf", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--county",
        action="append",
        default=[],
        help="County mapping as FIPS=County Name. Can be passed repeatedly.",
    )
    parser.add_argument(
        "--county-fips",
        help=(
            "CSV mapping county FIPS codes to names. Supports Census "
            "national_county.txt columns or county_fips/county_name columns."
        ),
    )
    parser.add_argument("--zip-puf")
    parser.add_argument(
        "--zip-examples",
        action="append",
        default=[],
        help="ZIP mapping as FIPS=ZIP,ZIP. Can be passed repeatedly.",
    )
    parser.add_argument("--year", type=int, default=2026)
    args = parser.parse_args(argv)

    county_mapping = _parse_county_mapping(args.county)
    if args.county_fips:
        county_mapping = {
            **load_county_fips_mapping(args.county_fips),
            **county_mapping,
        }

    fixture = build_enrollment_context_fixture(
        args.county_puf,
        county_mapping,
        zip_puf_path=args.zip_puf,
        zip_examples_by_county_fips=_parse_zip_mapping(args.zip_examples),
        year=args.year,
    )
    write_enrollment_context_fixture(args.output, fixture)


if __name__ == "__main__":
    main()
