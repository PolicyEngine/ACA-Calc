"""CMS Marketplace enrollment context helpers."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_ENROLLMENT_PATH = DATA_DIR / "enrollment_context_2026_counties.json"
DEFAULT_MODELED_COUNTY_PATH = (
    DATA_DIR / "enrollment_context_2026_modeled_counties.json"
)
DEFAULT_PLATFORM_PATH = DATA_DIR / "marketplace_platforms_2026.json"
DEFAULT_STATE_PATH = DATA_DIR / "enrollment_context_2026_states.json"


@dataclass(frozen=True)
class EnrollmentContext:
    """Local Marketplace enrollment context for one state/county selection."""

    year: int
    state: str
    county: str | None
    status: str
    marketplace_platform: str
    fine_grained_cms_available: bool
    county_context_available: bool
    message: str
    state_context_available: bool = False
    policyengine_modeled: bool = False
    source_level: str | None = None
    allocation_basis: str | None = None
    source: str | None = None
    source_url: str | None = None
    county_fips: str | None = None
    marketplace_plan_selections: int | None = None
    new_consumers: int | None = None
    returning_consumers: int | None = None
    consumers_with_aptc_or_csr: int | None = None
    aptc_consumers: int | None = None
    average_premium: float | None = None
    average_premium_after_aptc: float | None = None
    average_aptc: float | None = None
    consumers_premium_after_aptc_lte_10: int | None = None
    state_marketplace_plan_selections: int | None = None
    state_aptc_consumers: int | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


def load_marketplace_platforms(
    path: str | Path = DEFAULT_PLATFORM_PATH,
) -> dict[str, Any]:
    """Load the 2026 platform configuration."""
    with Path(path).open() as f:
        return json.load(f)


def load_enrollment_records(
    path: str | Path = DEFAULT_ENROLLMENT_PATH,
) -> dict[str, Any]:
    """Load processed enrollment records.

    The default is a checked-in compact county extract generated from CMS
    County-Level PUF rows. Future ingestion can point this function at a larger
    processed CMS output with the same field names.
    """
    with Path(path).open() as f:
        return json.load(f)


def load_state_records(
    path: str | Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    """Load observed CMS state-level Marketplace enrollment records."""
    with Path(path).open() as f:
        return json.load(f)


def load_modeled_county_records(
    path: str | Path = DEFAULT_MODELED_COUNTY_PATH,
) -> dict[str, Any]:
    """Load PolicyEngine-modeled SBM county backfill records."""
    with Path(path).open() as f:
        return json.load(f)


def _normalize_state(state: str | None) -> str:
    return (state or "").strip().upper()


def _normalize_county(county: str | None) -> str:
    value = (county or "").strip().casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    for suffix in (
        " city and borough",
        " census area",
        " municipality",
        " borough",
        " county",
        " parish",
    ):
        if value.endswith(suffix):
            value = value.removesuffix(suffix).strip()
            break
    return value


def _county_keys(county: str | None) -> tuple[str, str]:
    normalized = _normalize_county(county)
    return normalized, normalized.replace(" ", "")


def _platform_for_state(state: str, platforms: dict[str, Any]) -> str:
    if state in platforms["healthcare_gov_states"]:
        return "HealthCare.gov"
    if state in platforms["state_based_marketplace_states"]:
        return "State-based marketplace"
    return "Unknown"


def _record_index(records: list[dict[str, Any]]) -> dict[tuple[str, str], dict]:
    index = {}
    for record in records:
        for county_key in _county_keys(record["county"]):
            index[(record["state"].upper(), county_key)] = record
    return index


def get_enrollment_context(
    state: str,
    county: str | None = None,
    *,
    enrollment_path: str | Path = DEFAULT_ENROLLMENT_PATH,
    modeled_county_path: str | Path = DEFAULT_MODELED_COUNTY_PATH,
    platform_path: str | Path = DEFAULT_PLATFORM_PATH,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> EnrollmentContext:
    """Return CMS Marketplace enrollment context for a state/county.

    HealthCare.gov-platform states can have county/ZIP PUF detail. State-based
    marketplace states return a clear fallback status because CMS does not
    publish those county/ZIP PUF rows for them.
    """
    platforms = load_marketplace_platforms(platform_path)
    enrollment_data = load_enrollment_records(enrollment_path)
    modeled_county_data = load_modeled_county_records(modeled_county_path)
    state_data = load_state_records(state_path)
    state_code = _normalize_state(state)
    platform = _platform_for_state(state_code, platforms)
    year = enrollment_data.get("year", platforms.get("year", 2026))
    source = enrollment_data.get("source")
    source_url = enrollment_data.get("source_url")
    state_record = next(
        (
            record
            for record in state_data.get("records", [])
            if record["state"].upper() == state_code
        ),
        None,
    )

    if platform == "Unknown":
        return EnrollmentContext(
            year=year,
            state=state_code,
            county=county,
            status="unknown_state",
            marketplace_platform=platform,
            fine_grained_cms_available=False,
            county_context_available=False,
            state_context_available=False,
            message=(
                f"{state_code or 'This state'} is not recognized in the "
                "2026 Marketplace platform configuration."
            ),
            source=source,
            source_url=source_url,
        )

    if platform == "State-based marketplace":
        modeled_index = _record_index(modeled_county_data.get("records", []))
        modeled_record = next(
            (
                modeled_index[(state_code, county_key)]
                for county_key in _county_keys(county)
                if (state_code, county_key) in modeled_index
            ),
            None,
        )
        if modeled_record is not None:
            return EnrollmentContext(
                year=year,
                state=state_code,
                county=modeled_record["county"],
                status="policyengine_modeled_county_backfill",
                marketplace_platform=platform,
                fine_grained_cms_available=False,
                county_context_available=True,
                state_context_available=state_record is not None,
                policyengine_modeled=True,
                source_level=modeled_record.get("source_level"),
                allocation_basis=modeled_record.get("allocation_basis"),
                message=(
                    f"{state_code} runs a state-based marketplace. CMS reports "
                    "observed state-level enrollment, and this county value is "
                    "a PolicyEngine-modeled local backfill."
                ),
                source=modeled_county_data.get("source"),
                source_url=modeled_county_data.get("source_url"),
                county_fips=modeled_record.get("county_fips"),
                marketplace_plan_selections=modeled_record.get(
                    "marketplace_plan_selections"
                ),
                new_consumers=modeled_record.get("new_consumers"),
                returning_consumers=modeled_record.get("returning_consumers"),
                consumers_with_aptc_or_csr=modeled_record.get(
                    "consumers_with_aptc_or_csr"
                ),
                aptc_consumers=modeled_record.get("aptc_consumers"),
                average_premium=modeled_record.get("average_premium"),
                average_premium_after_aptc=modeled_record.get(
                    "average_premium_after_aptc"
                ),
                average_aptc=modeled_record.get("average_aptc"),
                consumers_premium_after_aptc_lte_10=modeled_record.get(
                    "consumers_premium_after_aptc_lte_10"
                ),
                state_marketplace_plan_selections=(
                    state_record or {}
                ).get("marketplace_plan_selections"),
                state_aptc_consumers=(state_record or {}).get("aptc_consumers"),
            )

        return EnrollmentContext(
            year=year,
            state=state_code,
            county=county,
            status="state_based_marketplace_fallback",
            marketplace_platform=platform,
            fine_grained_cms_available=False,
            county_context_available=False,
            state_context_available=state_record is not None,
            source_level=(state_record or {}).get("source_level"),
            message=(
                f"{state_code} runs a state-based marketplace. CMS county/ZIP "
                "Marketplace PUF detail is not available here, so this view "
                "falls back to state-level context only."
            ),
            source=state_data.get("source"),
            source_url=state_data.get("source_url"),
            marketplace_plan_selections=(state_record or {}).get(
                "marketplace_plan_selections"
            ),
            aptc_consumers=(state_record or {}).get("aptc_consumers"),
            average_premium=(state_record or {}).get("average_premium"),
            average_premium_after_aptc=(state_record or {}).get(
                "average_premium_after_aptc"
            ),
            average_aptc=(state_record or {}).get("average_aptc"),
        )

    index = _record_index(enrollment_data.get("records", []))
    record = next(
        (
            index[(state_code, county_key)]
            for county_key in _county_keys(county)
            if (state_code, county_key) in index
        ),
        None,
    )

    if record is None:
        location = f"{county}, {state_code}" if county else state_code
        return EnrollmentContext(
            year=year,
            state=state_code,
            county=county,
            status="not_in_compact_dataset",
            marketplace_platform=platform,
            fine_grained_cms_available=True,
            county_context_available=False,
            state_context_available=state_record is not None,
            message=(
                f"CMS county/ZIP PUF detail is available for {state_code}, "
                f"but {location} is not included in the checked-in compact "
                "county dataset yet."
            ),
            source=source,
            source_url=source_url,
        )

    return EnrollmentContext(
        year=year,
        state=state_code,
        county=record["county"],
        status="county_context_available",
        marketplace_platform=platform,
        fine_grained_cms_available=True,
        county_context_available=True,
        state_context_available=state_record is not None,
        source_level=record.get("source_level", "cms_county_puf"),
        message=(
            f"Fine-grained CMS county enrollment context is available for "
            f"{record['county']}, {state_code}."
        ),
        source=source,
        source_url=source_url,
        county_fips=record.get("county_fips"),
        marketplace_plan_selections=record.get("marketplace_plan_selections"),
        new_consumers=record.get("new_consumers"),
        returning_consumers=record.get("returning_consumers"),
        consumers_with_aptc_or_csr=record.get("consumers_with_aptc_or_csr"),
        aptc_consumers=record.get("aptc_consumers"),
        average_premium=record.get("average_premium"),
        average_premium_after_aptc=record.get("average_premium_after_aptc"),
        average_aptc=record.get("average_aptc"),
        consumers_premium_after_aptc_lte_10=record.get(
            "consumers_premium_after_aptc_lte_10"
        ),
    )
