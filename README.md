# ACA Premium Tax Credit Calculator

Compare 2026 Premium Tax Credits with and without Inflation Reduction Act
(IRA) enhancements, and pair household impacts with local Marketplace
enrollment context.

**Try the calculator:** https://www.policyengine.org/us/aca-calc#calculator

## Overview

The Inflation Reduction Act enhanced ACA subsidies through 2025. This
calculator shows what household credits would be in 2026 with and without
extending those enhancements.

Key differences:

- **With IRA extension:** no income cap, lower premium contributions
  (0-8.5% of income)
- **After IRA expires:** 400% FPL cap ("subsidy cliff"), higher contributions
  (2-9.5% of income)
- **Local impact:** Marketplace enrollment context for HealthCare.gov-platform
  geographies where fine-grained CMS PUF data are available

## Quick Start

### Run Locally

```bash
npm install
npm run dev
```

The React app runs at http://localhost:3000/us/aca-calc by default. The
calculator is available at http://localhost:3000/us/aca-calc#calculator.

Python tests and data utilities use the Python package in `aca_calc/`:

```bash
uv run pytest
```

## Features

- All 50 states plus DC
- County-specific ACA pricing inputs
- Interactive household calculator for baseline, IRA extension, and additional
  reform scenarios
- Local impact page with county and congressional district Marketplace
  enrollment context
- Compact checked-in CMS-style enrollment extracts, structured for later
  ingestion of processed full PUF files

## Example Results

| Scenario | Income | Baseline PTC | With IRA | Savings |
|----------|--------|--------------|----------|---------|
| NJ Family of 3 | $50,000 | $8,515 | $10,626 | $2,111/year |
| TX Couple (Travis) | $60,000 | $6,974 | $9,195 | $2,221/year |
| CA Couple + Child | $75,000 | $12,913 | $15,695 | $2,782/year |
| NY Single @ 400% FPL | $62,280 | $0 | $2,899 | $2,899/year |

## Technical Details

Built with:

- **Next.js + React:** interactive web application
- **PolicyEngine US:** open-source tax-benefit microsimulation
- **Recharts + D3:** data visualization
- **Python utilities:** enrollment fixture loaders and ingest helpers

County data are sourced from PolicyEngine's ACA rating area data. Enrollment
context starts with compact checked-in extracts under `aca_calc/data/` and can
be repointed to processed CMS Marketplace PUF files later.

## Project Structure

```text
.
├── app/                         # Next.js app shell
├── src/                         # React UI, pages, and client-side helpers
│   ├── components/              # Calculator, charts, and shared components
│   └── views/LocalImpact.jsx    # Local impact view
├── aca_calc/                    # Python calculation and data-access helpers
│   ├── calculations/            # PolicyEngine household/PTC utilities
│   └── data/                    # Compact checked-in enrollment extracts
├── tests/                       # Python unit tests
├── package.json                 # React/Next scripts
├── pyproject.toml               # Python package/dependencies
└── requirements.txt             # Python runtime dependencies
```

## Development

```bash
npm run build
uv run pytest
```

To update county data:

```bash
python process_counties.py
```

## License

Open source - see PolicyEngine US license for underlying calculations.

## Credits

Calculations powered by [PolicyEngine US](https://github.com/PolicyEngine/policyengine-us).
