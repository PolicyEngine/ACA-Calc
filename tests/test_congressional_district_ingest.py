"""Tests for congressional district context ingestion helpers."""

import json

from aca_calc.congressional_district_ingest import (
    build_district_enrollment_data,
    build_district_enrollment_records,
    build_district_enrollment_records_from_population_distribution,
)


def test_build_district_records_apportions_split_county_by_land_area(tmp_path):
    relationship = tmp_path / "relationship.txt"
    relationship.write_text(
        "\ufeffOID_CD119_20|GEOID_CD119_20|NAMELSAD_CD119_20|"
        "AREALAND_CD119_20|AREAWATER_CD119_20|MTFCC_CD119_20|"
        "FUNCSTAT_CD119_20|OID_COUNTY_20|GEOID_COUNTY_20|"
        "NAMELSAD_COUNTY_20|AREALAND_COUNTY_20|AREAWATER_COUNTY_20|"
        "MTFCC_COUNTY_20|CLASSFP_COUNTY_20|FUNCSTAT_COUNTY_20|"
        "AREALAND_PART|AREAWATER_PART\n"
        "1|4801|Congressional District 1|100|0|G5200|N|1|48001|"
        "Example County|100|0|G4020|H1|A|25|0\n"
        "2|4802|Congressional District 2|100|0|G5200|N|1|48001|"
        "Example County|100|0|G4020|H1|A|75|0\n"
    )
    enrollment_data = {
        "records": [
            {
                "state": "TX",
                "county_fips": "48001",
                "marketplace_plan_selections": 1000,
                "new_consumers": 200,
                "returning_consumers": 800,
                "consumers_with_aptc_or_csr": 900,
                "aptc_consumers": 700,
                "average_premium": 600,
                "average_premium_after_aptc": 120,
                "average_aptc": 500,
                "consumers_premium_after_aptc_lte_10": 300,
            }
        ]
    }

    records = build_district_enrollment_records(enrollment_data, relationship)

    assert [record["district_geoid"] for record in records] == ["4801", "4802"]
    assert records[0]["marketplace_plan_selections"] == 250
    assert records[1]["marketplace_plan_selections"] == 750
    assert records[0]["average_premium"] == 600
    assert records[1]["average_aptc"] == 500
    assert records[0]["source_county_count"] == 1


def test_build_district_enrollment_data_wraps_metadata(tmp_path):
    enrollment = tmp_path / "enrollment.json"
    relationship = tmp_path / "relationship.txt"
    enrollment.write_text(
        json.dumps(
            {
                "year": 2026,
                "records": [
                    {
                        "state": "TX",
                        "county_fips": "48001",
                        "marketplace_plan_selections": 10,
                    }
                ],
            }
        )
    )
    relationship.write_text(
        "OID_CD119_20|GEOID_CD119_20|NAMELSAD_CD119_20|"
        "AREALAND_CD119_20|AREAWATER_CD119_20|MTFCC_CD119_20|"
        "FUNCSTAT_CD119_20|OID_COUNTY_20|GEOID_COUNTY_20|"
        "NAMELSAD_COUNTY_20|AREALAND_COUNTY_20|AREAWATER_COUNTY_20|"
        "MTFCC_COUNTY_20|CLASSFP_COUNTY_20|FUNCSTAT_COUNTY_20|"
        "AREALAND_PART|AREAWATER_PART\n"
        "1|4801|Congressional District 1|100|0|G5200|N|1|48001|"
        "Example County|100|0|G4020|H1|A|100|0\n"
    )

    district_data = build_district_enrollment_data(enrollment, relationship)

    assert district_data["year"] == 2026
    assert district_data["congress"] == 119
    assert district_data["records"][0]["district_label"] == "TX-01"


def test_build_district_records_uses_policyengine_population_distribution(
    tmp_path,
):
    distribution = tmp_path / "county_cd_distributions.csv"
    distribution.write_text(
        "cd_geoid,county_fips,probability\n"
        "4801,48001,0.20\n"
        "4802,48001,0.30\n"
        "4801,48003,0.80\n"
        "4802,48003,0.70\n"
    )
    enrollment_data = {
        "records": [
            {
                "state": "TX",
                "county": "Example County",
                "county_fips": "48001",
                "marketplace_plan_selections": 1000,
                "aptc_consumers": 800,
                "average_premium_after_aptc": 100,
            },
            {
                "state": "TX",
                "county": "Second County",
                "county_fips": "48003",
                "marketplace_plan_selections": 500,
                "aptc_consumers": 300,
                "average_premium_after_aptc": 200,
            },
        ]
    }

    records = build_district_enrollment_records_from_population_distribution(
        enrollment_data,
        distribution,
    )

    assert [record["district_geoid"] for record in records] == ["4801", "4802"]
    assert records[0]["marketplace_plan_selections"] == 667
    assert records[1]["marketplace_plan_selections"] == 833
    assert records[0]["aptc_consumers"] == 480
    assert records[1]["aptc_consumers"] == 620
    assert records[0]["source_county_count"] == 2
