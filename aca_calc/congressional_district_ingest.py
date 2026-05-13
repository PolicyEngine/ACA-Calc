"""Build compact congressional district context from Census and CMS inputs."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


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

COUNT_FIELDS = (
    "marketplace_plan_selections",
    "new_consumers",
    "returning_consumers",
    "consumers_with_aptc_or_csr",
    "aptc_consumers",
    "consumers_premium_after_aptc_lte_10",
)


def _int_value(value: Any) -> int:
    if value is None:
        return 0
    return int(round(float(value)))


def _float_value(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_coordinates(value: str) -> list[list[float]]:
    coordinates = []
    for coordinate in value.split():
        lon, lat, *_ = coordinate.split(",")
        coordinates.append([round(float(lon), 5), round(float(lat), 5)])
    return list(reversed(coordinates))


def _district_label(state: str, district: str, namelsad: str) -> str:
    if district == "00":
        return f"{state} at-large"
    return f"{state}-{int(district):02d}" if district.isdigit() else namelsad


def _district_name(district: str) -> str:
    if district == "00":
        return "Congressional District (at Large)"
    return f"Congressional District {int(district)}"


def _county_enum_name(county: str, state: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", county)
        .encode("ascii", "ignore")
        .decode("ascii")
        .upper()
    )
    normalized = re.sub(r"[.'\"]", "", normalized)
    normalized = re.sub(r"[^A-Z0-9]+", "_", normalized).strip("_")
    return f"{normalized}_{state}"


def build_district_geography(kml_path: str | Path) -> dict[str, Any]:
    """Parse Census cartographic boundary KML into compact GeoJSON."""
    namespace = {"kml": "http://www.opengis.net/kml/2.2"}
    root = ET.parse(kml_path).getroot()
    features = []

    for placemark in root.findall(".//kml:Placemark", namespace):
        data = {
            item.attrib["name"]: item.text or ""
            for item in placemark.findall(".//kml:SimpleData", namespace)
        }
        state_fips = data.get("STATEFP")
        state = STATE_FIPS_TO_ABBR.get(state_fips or "")
        if state is None:
            continue

        polygons = []
        for polygon in placemark.findall(".//kml:Polygon", namespace):
            rings = []
            outer = polygon.find(
                "./kml:outerBoundaryIs/kml:LinearRing/kml:coordinates",
                namespace,
            )
            if outer is not None and outer.text:
                rings.append(_parse_coordinates(outer.text))

            for inner in polygon.findall(
                "./kml:innerBoundaryIs/kml:LinearRing/kml:coordinates",
                namespace,
            ):
                if inner.text:
                    rings.append(_parse_coordinates(inner.text))

            if rings:
                polygons.append(rings)

        district = data["CD119FP"]
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "geoid": data["GEOID"],
                    "state": state,
                    "state_fips": state_fips,
                    "district": district,
                    "label": _district_label(
                        state,
                        district,
                        data["NAMELSAD"],
                    ),
                    "namelsad": data["NAMELSAD"],
                },
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": polygons,
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "congress": 119,
        "source": "U.S. Census Bureau 2024 Cartographic Boundary File, 119th Congressional Districts, 1:20,000,000",
        "source_url": "https://www2.census.gov/geo/tiger/GENZ2024/kml/cb_2024_us_cd119_20m.zip",
        "features": sorted(
            features,
            key=lambda feature: feature["properties"]["geoid"],
        ),
    }


def _empty_accumulator_for_district(
    geoid: str,
    state: str,
    district_name: str | None = None,
) -> dict[str, Any]:
    district = geoid[2:]
    return {
        "state": state,
        "district_geoid": geoid,
        "district": district,
        "district_label": _district_label(
            state,
            district,
            district_name or _district_name(district),
        ),
        "district_name": district_name or _district_name(district),
        "source_counties": set(),
        "county_part_count": 0,
        "weighted": {field: 0.0 for field in COUNT_FIELDS},
        "premium_weight": 0.0,
        "premium_denominator": 0.0,
        "premium_after_aptc_weight": 0.0,
        "premium_after_aptc_denominator": 0.0,
        "aptc_weight": 0.0,
        "aptc_denominator": 0.0,
    }


def _empty_accumulator(row: dict[str, str], state: str) -> dict[str, Any]:
    return _empty_accumulator_for_district(
        row["GEOID_CD119_20"],
        state,
        row["NAMELSAD_CD119_20"],
    )


def _accumulate_county(
    accumulator: dict[str, Any],
    county_record: dict[str, Any],
    weight: float,
    source_county: str,
) -> None:
    accumulator["source_counties"].add(source_county)
    accumulator["county_part_count"] += 1

    for field in COUNT_FIELDS:
        accumulator["weighted"][field] += _int_value(county_record.get(field)) * weight

    plan_selections = (
        _int_value(county_record.get("marketplace_plan_selections")) * weight
    )
    aptc_consumers = _int_value(county_record.get("aptc_consumers")) * weight
    average_premium = _float_value(county_record.get("average_premium"))
    average_premium_after_aptc = _float_value(
        county_record.get("average_premium_after_aptc")
    )
    average_aptc = _float_value(county_record.get("average_aptc"))

    if average_premium is not None and plan_selections:
        accumulator["premium_weight"] += average_premium * plan_selections
        accumulator["premium_denominator"] += plan_selections
    if average_premium_after_aptc is not None and plan_selections:
        accumulator["premium_after_aptc_weight"] += (
            average_premium_after_aptc * plan_selections
        )
        accumulator["premium_after_aptc_denominator"] += plan_selections
    if average_aptc is not None and aptc_consumers:
        accumulator["aptc_weight"] += average_aptc * aptc_consumers
        accumulator["aptc_denominator"] += aptc_consumers


def _records_from_accumulators(
    district_accumulators: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    records = []
    for accumulator in district_accumulators.values():
        premium_denominator = accumulator["premium_denominator"]
        premium_after_aptc_denominator = accumulator[
            "premium_after_aptc_denominator"
        ]
        aptc_denominator = accumulator["aptc_denominator"]
        records.append(
            {
                "state": accumulator["state"],
                "district_geoid": accumulator["district_geoid"],
                "district": accumulator["district"],
                "district_label": accumulator["district_label"],
                "district_name": accumulator["district_name"],
                "marketplace_plan_selections": round(
                    accumulator["weighted"]["marketplace_plan_selections"]
                ),
                "new_consumers": round(accumulator["weighted"]["new_consumers"]),
                "returning_consumers": round(
                    accumulator["weighted"]["returning_consumers"]
                ),
                "consumers_with_aptc_or_csr": round(
                    accumulator["weighted"]["consumers_with_aptc_or_csr"]
                ),
                "aptc_consumers": round(accumulator["weighted"]["aptc_consumers"]),
                "average_premium": (
                    round(accumulator["premium_weight"] / premium_denominator)
                    if premium_denominator
                    else None
                ),
                "average_premium_after_aptc": (
                    round(
                        accumulator["premium_after_aptc_weight"]
                        / premium_after_aptc_denominator
                    )
                    if premium_after_aptc_denominator
                    else None
                ),
                "average_aptc": (
                    round(accumulator["aptc_weight"] / aptc_denominator)
                    if aptc_denominator
                    else None
                ),
                "consumers_premium_after_aptc_lte_10": round(
                    accumulator["weighted"]["consumers_premium_after_aptc_lte_10"]
                ),
                "source_county_count": len(accumulator["source_counties"]),
                "county_part_count": accumulator["county_part_count"],
            }
        )

    return sorted(
        records,
        key=lambda record: (record["state"], record["district"]),
    )


def build_district_enrollment_records(
    enrollment_data: dict[str, Any],
    relationship_path: str | Path,
) -> list[dict[str, Any]]:
    """Aggregate county CMS rows to 119th congressional districts.

    Split counties are apportioned by Census county-to-district land-area
    overlap. This keeps the first slice deterministic while leaving room for a
    future ZIP/block allocation.
    """
    county_records = {
        record["county_fips"]: record
        for record in enrollment_data.get("records", [])
        if record.get("county_fips")
    }
    district_accumulators: dict[str, dict[str, Any]] = {}

    with Path(relationship_path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="|")
        for row in reader:
            county_record = county_records.get(row["GEOID_COUNTY_20"])
            if county_record is None:
                continue

            county_land_area = _float_value(row["AREALAND_COUNTY_20"]) or 0
            part_land_area = _float_value(row["AREALAND_PART"]) or 0
            if county_land_area <= 0 or part_land_area <= 0:
                continue

            weight = part_land_area / county_land_area
            district_geoid = row["GEOID_CD119_20"]
            state = county_record["state"]
            accumulator = district_accumulators.setdefault(
                district_geoid,
                _empty_accumulator(row, state),
            )
            _accumulate_county(
                accumulator,
                county_record,
                weight,
                row["GEOID_COUNTY_20"],
            )

    return _records_from_accumulators(district_accumulators)


def build_district_enrollment_records_from_population_distribution(
    enrollment_data: dict[str, Any],
    distribution_path: str | Path,
) -> list[dict[str, Any]]:
    """Aggregate county CMS rows with PolicyEngine population CD distributions.

    The PolicyEngine US Data input starts as P(block | congressional district),
    built from Census 2020 block population and 119th Congressional District
    block equivalency files. This repo stores a compact county aggregation of
    that file as P(county | congressional district). Because districts are
    population balanced within states, normalizing those rows within each county
    gives an estimate of P(congressional district | county) for allocating
    county-level CMS rows.
    """
    county_records_by_fips = {
        record["county_fips"]: record
        for record in enrollment_data.get("records", [])
        if record.get("county_fips")
    }
    county_records_by_name = {
        _county_enum_name(record["county"], record["state"]): record
        for record in enrollment_data.get("records", [])
        if record.get("county") and record.get("state")
    }
    distribution_rows = []
    county_probability_totals: dict[str, float] = {}

    with Path(distribution_path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            county_key = row.get("county_fips") or row.get("county_name")
            if county_key is None:
                continue

            county_record = county_records_by_fips.get(
                county_key,
            ) or county_records_by_name.get(county_key)
            if county_record is None:
                continue

            probability = _float_value(row["probability"]) or 0
            if probability <= 0:
                continue

            district_geoid = f"{int(row['cd_geoid']):04d}"
            distribution_rows.append(
                (district_geoid, county_key, county_record, probability)
            )
            county_probability_totals[county_key] = (
                county_probability_totals.get(county_key, 0) + probability
            )

    district_accumulators: dict[str, dict[str, Any]] = {}
    for district_geoid, county_key, county_record, probability in distribution_rows:
        probability_total = county_probability_totals[county_key]
        if probability_total <= 0:
            continue

        state = county_record["state"]
        accumulator = district_accumulators.setdefault(
            district_geoid,
            _empty_accumulator_for_district(district_geoid, state),
        )
        _accumulate_county(
            accumulator,
            county_record,
            probability / probability_total,
            county_record["county_fips"],
        )

    return _records_from_accumulators(district_accumulators)


def _uses_population_distribution(path: str | Path) -> bool:
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        return (
            {"cd_geoid", "probability"}.issubset(fields)
            and bool({"county_fips", "county_name"} & fields)
        )


def build_district_enrollment_data(
    enrollment_path: str | Path,
    relationship_path: str | Path,
) -> dict[str, Any]:
    with Path(enrollment_path).open() as f:
        enrollment_data = json.load(f)

    if _uses_population_distribution(relationship_path):
        return {
            "year": enrollment_data.get("year", 2026),
            "congress": 119,
            "geography": "119th Congressional District",
            "source": (
                "CMS 2026 Marketplace Open Enrollment County-Level PUF and "
                "PolicyEngine US Data block-to-congressional-district "
                "population distributions"
            ),
            "source_url": (
                "https://github.com/PolicyEngine/policyengine-us-data/blob/"
                "master/policyengine_us_data/storage/calibration_targets/"
                "make_block_cd_distributions.py"
            ),
            "allocation_method": (
                "County-level CMS PUF rows are apportioned to 119th "
                "congressional districts with county shares aggregated from "
                "PolicyEngine US Data's population-weighted 2020 Census block "
                "distributions."
            ),
            "records": build_district_enrollment_records_from_population_distribution(
                enrollment_data,
                relationship_path,
            ),
        }

    return {
        "year": enrollment_data.get("year", 2026),
        "congress": 119,
        "geography": "119th Congressional District",
        "source": "CMS 2026 Marketplace Open Enrollment County-Level PUF and U.S. Census Bureau 119th congressional district relationship files",
        "source_url": "https://www.census.gov/geographies/reference-files/2020/geo/relationship-files.html",
        "allocation_method": "County-level CMS PUF rows are apportioned to 119th congressional districts by Census county-to-district land-area overlap.",
        "records": build_district_enrollment_records(
            enrollment_data,
            relationship_path,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--district-kml")
    parser.add_argument("--district-geo-output")
    parser.add_argument("--enrollment-context")
    parser.add_argument("--relationship-file")
    parser.add_argument("--district-context-output")
    args = parser.parse_args()

    if args.district_kml and args.district_geo_output:
        geography = build_district_geography(args.district_kml)
        Path(args.district_geo_output).write_text(
            json.dumps(geography, separators=(",", ":")) + "\n"
        )

    if (
        args.enrollment_context
        and args.relationship_file
        and args.district_context_output
    ):
        context = build_district_enrollment_data(
            args.enrollment_context,
            args.relationship_file,
        )
        Path(args.district_context_output).write_text(
            json.dumps(context, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
