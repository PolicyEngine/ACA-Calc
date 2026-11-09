# Contributing Guide

## Code Structure

### API (`src/aca_api/`)

- **`api.py`**: the FastAPI app.
  - `/api/calculate-stream`, which the calculator page calls, and `/api/calculate`, its fallback, run current law and the selected scenarios across an income axis for one household.
  - `/api/explain` asks Claude for a narrative built from the computed numbers.
  - `/api/health` reports that the API is up.
- **`models.py`**: the request and response models.

### Calculations (`aca_calc/calculations/`)

- **`household.py`**: `build_household_situation()` builds the PolicyEngine situation, with an employment income axis for the charts.
  - County format: "Travis County" → "TRAVIS_COUNTY_TX".
- **`reforms.py`**: each scenario as a PolicyEngine reform.

### Frontend

- **`app/`**: the Next.js entry.
- **`src/App.jsx`**: the Overview, Explore Households and Calculator pages.
- **`src/components/`**: the charts, tables and the calculator.
- **`src/data/households/`**: precomputed results that the Overview and Explore pages read. `precompute_households.py` and `precompute_cliff_household.py` regenerate them.

### Data Files

- **`counties.json`**: 3,143 counties across all 50 states + DC.
- **`process_counties.py`**: updates county data from PolicyEngine.

## Testing

```bash
# Every Python test
make test

# The API tests CI runs, against the Modal image's exact packages: the
# test files listed in .github/workflows/modal-api.yml
uv venv --python 3.11
uv pip install -r modal-requirements.txt
.venv/bin/python -m pytest tests/test_api_explain.py tests/test_smoke_test_api.py
```

## PolicyEngine Integration

### Household Structure Pattern

```python
situation = {
    "people": {...},
    "families": {...},
    "spm_units": {...},      # Required!
    "tax_units": {...},
    "households": {...},
    "marital_units": {...}   # If married/partnered
}
```

**Important**: Always include `spm_units` for accurate ACA calculations.

### Reform Parameters

The scenarios change these policyengine-us parameters:
- `gov.aca.required_contribution_percentage.threshold`, `.initial` and `.final`: the contribution schedule, three lists replaced together.
- `gov.aca.ptc_income_eligibility[2]`: the 400% FPL limit.

Other scenarios use policyengine-us's contributed reforms (`policyengine_us.reforms.aca`).

### County Format

PolicyEngine expects: `COUNTY_NAME_STATE`
- Examples: `TRAVIS_COUNTY_TX`, `BERGEN_COUNTY_NJ`
- All caps, underscores instead of spaces
- State abbreviation suffix

## Common Issues

### SLCSP Returns $0
- Check county name format
- Verify state has marketplace data
- Try without county (uses state default)

### A Scenario Fails
- A reform that names a parameter policyengine-us no longer has fails the request. The API reports the error, and the page shows it, rather than zero credits.
- Check the reform's parameter paths against the installed policyengine-us.

## Questions?

Check PolicyEngine docs: https://policyengine.github.io/policyengine-us/
