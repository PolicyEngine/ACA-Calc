# Contributing Guide

## Code Structure

### Main Application (`app.py`)

**Key Functions:**

1. **`calculate_ptc()`** - Core calculation logic
   - Builds household situation dictionary
   - Applies reform parameters if requested
   - Returns PTC and SLCSP values
   - County format: "Travis County" → "TRAVIS_COUNTY_TX"

2. **`create_chart()`** - Visualization
   - Generates income sweep curves
   - Shows user's position on curves
   - Compares baseline vs reform scenarios

3. **`main()`** - Streamlit UI
   - Handles user inputs
   - Displays results
   - Manages session state

### Data Files

- **`counties.json`**: 3,143 counties across all 50 states + DC
- **`process_counties.py`**: Updates county data from PolicyEngine

## Testing

```bash
# Quick verification test
python tests/test_reform_verification.py

# Comprehensive tests
python tests/test_app_comprehensive.py

# State-specific tests
python tests/test_texas.py
python tests/test_nj.py
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

IRA enhancements modify these PolicyEngine parameters:
```python
"gov.aca.ptc_phase_out_rate[0-6].amount"  # Contribution percentages
"gov.aca.ptc_income_eligibility[2].amount"  # Remove 400% FPL cap
```

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

### Reform Not Applied
- Ensure `use_reform=True` parameter
- Check Reform.from_dict() imports correctly
- Verify date format: "2026-01-01.2100-12-31"

### Calculations Don't Match Notebook
- Check PolicyEngine version
- Verify household structure matches
- Confirm income is split correctly for couples

## Adding Features

### New State-Specific Logic
1. Add to `calculate_ptc()` function
2. Test with multiple counties in that state
3. Compare against PolicyEngine web app

### UI Changes
1. Modify `main()` function
2. Update session state handling
3. Test with various household types

### New Visualizations
1. Add to or modify `create_chart()`
2. Use Plotly for consistency
3. Include hover tooltips

## Performance Tips

- Use `@st.cache_data` for expensive operations
- Load counties.json once at startup
- Minimize redundant PolicyEngine simulations

## Questions?

Check PolicyEngine docs: https://policyengine.github.io/policyengine-us/