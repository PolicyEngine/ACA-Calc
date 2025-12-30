"""
Household situation building utilities for PolicyEngine simulations.
"""


def build_household_situation(
    age_head,
    age_spouse,
    dependent_ages,
    state,
    county=None,
    zip_code=None,
    year=2026,
    with_axes=False,
):
    """Build a PolicyEngine household situation.

    Args:
        age_head: Age of head of household
        age_spouse: Age of spouse (None if not married)
        dependent_ages: List of dependent ages
        state: Two-letter state code (e.g., "CA")
        county: County name (e.g., "Los Angeles County")
        zip_code: 5-digit ZIP code (required for LA County)
        year: Year for simulation
        with_axes: If True, add employment_income axis for income sweep

    Returns:
        dict: PolicyEngine situation dictionary
    """
    situation = {
        "people": {"you": {"age": {year: age_head}}},
        "families": {"your family": {"members": ["you"]}},
        "spm_units": {"your household": {"members": ["you"]}},
        "tax_units": {"your tax unit": {"members": ["you"]}},
        "households": {
            "your household": {"members": ["you"], "state_name": {year: state}}
        },
    }

    # Add axes if requested (for income sweeps)
    # 1,001 points is sufficient for smooth charts while being 10x faster than 10,001
    if with_axes:
        situation["axes"] = [
            [
                {
                    "name": "employment_income",
                    "count": 1_001,
                    "min": 0,
                    "max": 1000000,
                    "period": year,
                }
            ]
        ]

    # Add county if provided
    if county:
        county_pe_format = county.upper().replace(" ", "_") + "_" + state
        situation["households"]["your household"]["county"] = {
            year: county_pe_format
        }

    # Add ZIP code if provided (required for LA County)
    if zip_code:
        situation["households"]["your household"]["zip_code"] = {year: zip_code}

    # Add spouse if married
    if age_spouse:
        situation["people"]["your partner"] = {"age": {year: age_spouse}}
        situation["families"]["your family"]["members"].append("your partner")
        situation["spm_units"]["your household"]["members"].append("your partner")
        situation["tax_units"]["your tax unit"]["members"].append("your partner")
        situation["households"]["your household"]["members"].append("your partner")
        situation["marital_units"] = {
            "your marital unit": {"members": ["you", "your partner"]}
        }

    # Add dependents
    for i, dep_age in enumerate(dependent_ages):
        if i == 0:
            child_id = "your first dependent"
        elif i == 1:
            child_id = "your second dependent"
        else:
            child_id = f"dependent_{i+1}"

        situation["people"][child_id] = {"age": {year: dep_age}}
        situation["families"]["your family"]["members"].append(child_id)
        situation["spm_units"]["your household"]["members"].append(child_id)
        situation["tax_units"]["your tax unit"]["members"].append(child_id)
        situation["households"]["your household"]["members"].append(child_id)

        # Add child's marital unit
        if "marital_units" not in situation:
            situation["marital_units"] = {}
        situation["marital_units"][f"{child_id}'s marital unit"] = {
            "members": [child_id]
        }

    return situation
