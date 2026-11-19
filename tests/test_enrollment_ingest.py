"""Tests for CMS Marketplace enrollment PUF ingestion helpers."""

import csv

from aca_calc.enrollment_ingest import (
    build_enrollment_context_fixture,
    load_county_fips_mapping,
    parse_cms_number,
)


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_parse_cms_number_handles_counts_currency_and_suppression():
    assert parse_cms_number('"1,234"') == 1234
    assert parse_cms_number("1,234") == 1234
    assert parse_cms_number("$562 ") == 562
    assert parse_cms_number("*") is None
    assert parse_cms_number("+") is None


def test_build_enrollment_context_fixture_from_selected_rows(tmp_path):
    county_puf = tmp_path / "county.csv"
    zip_puf = tmp_path / "zip.csv"

    write_csv(
        county_puf,
        [
            "State_Abrvtn",
            "County_FIPS_Cd",
            "Cnsmr",
            "New_Cnsmr",
            "Tot_Renrl",
            "Cnsmr_Wth_APTC_CSR",
            "APTC_Cnsmr",
            "Avg_Prm",
            "Avg_Prm_Aftr_APTC",
            "APTC_Cnsmr_Avg_APTC",
            "Cnsmr_Prm_Aftr_APTC_LTEQ10",
        ],
        [
            {
                "State_Abrvtn": "TX",
                "County_FIPS_Cd": "48453",
                "Cnsmr": "184,355",
                "New_Cnsmr": "37,178",
                "Tot_Renrl": "147,177",
                "Cnsmr_Wth_APTC_CSR": "162,479",
                "APTC_Cnsmr": "162,349",
                "Avg_Prm": "$625 ",
                "Avg_Prm_Aftr_APTC": "$130 ",
                "APTC_Cnsmr_Avg_APTC": "$562 ",
                "Cnsmr_Prm_Aftr_APTC_LTEQ10": "83,892",
            },
            {
                "State_Abrvtn": "FL",
                "County_FIPS_Cd": "12057",
                "Cnsmr": "260,235",
                "New_Cnsmr": "39,390",
                "Tot_Renrl": "220,845",
                "Cnsmr_Wth_APTC_CSR": "245,436",
                "APTC_Cnsmr": "245,341",
                "Avg_Prm": "$757 ",
                "Avg_Prm_Aftr_APTC": "$108 ",
                "APTC_Cnsmr_Avg_APTC": "$688 ",
                "Cnsmr_Prm_Aftr_APTC_LTEQ10": "84,635",
            },
        ],
    )
    write_csv(
        zip_puf,
        ["zip", "Cnsmr", "APTC_Cnsmr", "APTC_Cnsmr_Avg_APTC"],
        [
            {
                "zip": "78701",
                "Cnsmr": "2,614",
                "APTC_Cnsmr": "2,097",
                "APTC_Cnsmr_Avg_APTC": "$616 ",
            },
            {
                "zip": "78702",
                "Cnsmr": "9,023",
                "APTC_Cnsmr": "8,324",
                "APTC_Cnsmr_Avg_APTC": "$480 ",
            },
        ],
    )

    fixture = build_enrollment_context_fixture(
        county_puf,
        {"48453": "Travis County"},
        zip_puf_path=zip_puf,
        zip_examples_by_county_fips={"48453": ["78702", "78701"]},
    )

    assert len(fixture["records"]) == 1
    record = fixture["records"][0]
    assert record["state"] == "TX"
    assert record["county"] == "Travis County"
    assert record["marketplace_plan_selections"] == 184_355
    assert record["aptc_consumers"] == 162_349
    assert record["average_aptc"] == 562
    assert record["zip_examples"][0]["zip"] == "78701"
    assert record["zip_examples"][1]["aptc_consumers"] == 8_324


def test_load_county_fips_mapping_from_census_shape(tmp_path):
    county_fips = tmp_path / "national_county.txt"
    write_csv(
        county_fips,
        ["STATE", "STATEFP", "COUNTYFP", "COUNTYNAME", "CLASSFP"],
        [
            {
                "STATE": "TX",
                "STATEFP": "48",
                "COUNTYFP": "453",
                "COUNTYNAME": "Travis County",
                "CLASSFP": "H1",
            }
        ],
    )

    assert load_county_fips_mapping(county_fips) == {
        "48453": "Travis County"
    }


def test_load_county_fips_mapping_from_headerless_census_file(tmp_path):
    county_fips = tmp_path / "national_county.txt"
    county_fips.write_text("TX,48,453,Travis County,H1\n")

    assert load_county_fips_mapping(county_fips) == {
        "48453": "Travis County"
    }
