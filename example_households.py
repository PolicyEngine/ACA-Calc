"""The four example households the Overview walks through.

Shared by precompute_households.py, which computes the Overview's table, and
precompute_calculator_examples.py, which stores the calculator's result for
each so the calculator can show it without a request. No dependencies, so the
calculator script runs anywhere.
"""

YEAR = 2027
PRIOR_YEAR = 2026

# Two households below current law's 400% FPL limit and two above it.
EXAMPLES = [
    {
        "key": "texas_single",
        "name": "Single adult",
        "description": "Age 40, Harris County, Texas",
        "household": dict(age_head=40, age_spouse=None, dependent_ages=[], state="TX", county="Harris County"),
        "income": 40_000,
    },
    {
        "key": "florida_family",
        "name": "Family of four",
        "description": "Parents aged 40, children aged 10 and 8, Hillsborough County, Florida",
        "household": dict(age_head=40, age_spouse=40, dependent_ages=[10, 8], state="FL", county="Hillsborough County"),
        "income": 75_000,
    },
    {
        "key": "pennsylvania_single",
        "name": "Single adult",
        "description": "Age 45, Lebanon County, Pennsylvania",
        "household": dict(age_head=45, age_spouse=None, dependent_ages=[], state="PA", county="Lebanon County"),
        "income": 104_000,
    },
    {
        "key": "california_couple",
        "name": "Couple in their 60s",
        "description": "Ages 64 and 62, San Benito County, California",
        "household": dict(age_head=64, age_spouse=62, dependent_ages=[], state="CA", county="San Benito County"),
        "income": 90_000,
    },
]
