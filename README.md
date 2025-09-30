# ACA Premium Tax Credit Calculator

Compare 2026 Premium Tax Credits with and without Inflation Reduction Act (IRA) enhancements.

**🔗 [Try the Calculator](https://policyengine-aca-calc.streamlit.app/)**

## Overview

The Inflation Reduction Act enhanced ACA subsidies through 2025. This calculator shows what your credits would be in 2026 with and without extending these enhancements.

**Key Differences:**
- **With IRA Extension**: No income cap, lower premium contributions (0-8.5% of income)
- **After IRA Expires**: 400% FPL cap ("subsidy cliff"), higher contributions (2-9.5% of income)

## Quick Start

### Use the Live App

Visit **[https://policyengine-aca-calc.streamlit.app/](https://policyengine-aca-calc.streamlit.app/)** to use the calculator immediately.

### Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app will open at http://localhost:8501

## Features

- ✅ **All 50 States + DC**: Accurate calculations for every jurisdiction
- ✅ **3,143 Counties**: County-specific marketplace pricing
- ✅ **Real-time Comparison**: Side-by-side baseline vs. IRA extension
- ✅ **Interactive Charts**: See how credits change across income levels
- ✅ **Household Flexibility**: Single, married, with/without dependents

## Example Results

| Scenario | Income | Baseline PTC | With IRA | Savings |
|----------|--------|--------------|----------|---------|
| NJ Family of 3 | $50,000 | $8,515 | $10,626 | $2,111/year |
| TX Couple (Travis) | $60,000 | $6,974 | $9,195 | $2,221/year |
| CA Couple + Child | $75,000 | $12,913 | $15,695 | $2,782/year |
| NY Single @ 400% FPL | $62,280 | $0 | $2,899 | $2,899/year |

## Technical Details

Built with:
- **[PolicyEngine US](https://policyengine.org)**: Open-source tax-benefit microsimulation
- **[Streamlit](https://streamlit.io)**: Interactive web interface
- **[Plotly](https://plotly.com)**: Data visualization

County data sourced from PolicyEngine's ACA rating areas database.

## Project Structure

```
.
├── app.py                  # Main Streamlit application
├── counties.json           # County data for all states
├── process_counties.py     # County data processor
├── requirements.txt        # Python dependencies
├── tests/                  # Test files
├── notebooks/              # Analysis notebooks
└── archive/                # Historical files
```

## Development

```bash
# Run tests
python tests/test_reform_verification.py

# Update county data
python process_counties.py
```

## License

Open source - see PolicyEngine US license for underlying calculations.

## Credits

Calculations powered by [PolicyEngine US](https://github.com/PolicyEngine/policyengine-us)