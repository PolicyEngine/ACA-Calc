# ACA Premium Tax Credit Calculator

Compare ACA premium tax credits under current law and under proposals to extend the enhanced credits, for 2026 and 2027 coverage.

**🔗 [Try the Calculator](https://policyengine.org/us/aca-calc)**

## Overview

The American Rescue Plan Act enhanced ACA premium tax credits for 2021 and 2022, and the Inflation Reduction Act extended them through 2025. They expired after 2025, so 2026 and 2027 coverage follows the original ACA schedule. The calculator shows a household's credits under current law and under proposals to extend the enhanced credits, such as H.R. 1834.

**Key Differences:**
- **Enhanced credits (2021–2025)**: No income cap; required contributions from 0% to 8.5% of income
- **Current law (2026 on)**: No credit above 400% FPL (the "subsidy cliff"); required contributions from about 2% to 10% of income, set each year by the IRS

## Quick Start

### Use the Live App

Visit **[https://policyengine.org/us/aca-calc](https://policyengine.org/us/aca-calc)** to use the calculator immediately.

### Run Locally

```bash
# The frontend, at http://localhost:3000/us/aca-calc
bun install
bun run dev

# The API, at http://localhost:5001, which the calculator page calls unless
# NEXT_PUBLIC_API_URL names another
uv run --with fastapi --with uvicorn uvicorn src.aca_api.api:app --port 5001
```

`make api` runs the API in Docker instead.

## Features

- ✅ **All 50 States + DC**: Accurate calculations for every jurisdiction
- ✅ **3,143 Counties**: County-specific marketplace pricing
- ✅ **Real-time Comparison**: Side-by-side baseline vs. IRA extension
- ✅ **Interactive Charts**: See how credits change across income levels
- ✅ **Household Flexibility**: Single, married, with/without dependents

## Technical Details

Built with:
- **[PolicyEngine US](https://policyengine.org)**: Open-source tax-benefit microsimulation
- **[Next.js](https://nextjs.org)** and **[Recharts](https://recharts.org)**: the frontend, on Vercel
- **[FastAPI](https://fastapi.tiangolo.com)**: the calculator's API, on Modal

County data sourced from PolicyEngine's ACA rating areas database.

## Project Structure

```
.
├── app/                    # Next.js entry (layout and page)
├── src/
│   ├── App.jsx             # The Overview, Explore Households and Calculator pages
│   ├── components/         # Charts, tables and the calculator
│   ├── data/households/    # Precomputed results the Overview and Explore pages read
│   └── aca_api/            # The FastAPI backend (api.py, models.py)
├── aca_calc/calculations/  # The household builder and the scenarios' reforms
├── modal_app.py            # The API's Modal deployment
├── modal-requirements.txt  # The API image's exact package versions
├── precompute_*.py         # Regenerate the precomputed household results
├── scripts/                # The post-deploy smoke test
├── counties.json           # County lists for the calculator form
├── process_counties.py     # Regenerates counties.json
├── tests/                  # Python tests
└── notebooks/              # Analysis notebooks
```

## Development

The optional `/api/explain` endpoint uses `claude-sonnet-5-5` with low effort
and requires `ANTHROPIC_API_KEY`. Run its regression tests without provider
credentials or network calls (FastAPI is installed separately in deployment):

```bash
uv sync --locked --extra dev
uv run --locked --with fastapi pytest tests/test_api_explain.py -v
```

```bash
# Run the Python tests
make test

# Update county data
python process_counties.py
```

## Deploying the API

The calculator page calls a FastAPI backend on Modal: app `aca-calc-api` in
the `main` environment of PolicyEngine's Modal workspace, defined in
`modal_app.py`. The `Modal API` workflow (`.github/workflows/modal-api.yml`)
runs the API tests against the image's pinned packages on pull requests that
touch the backend. When such a change merges to `main`, it deploys the app and
smoke-tests `/api/health`, both calculator endpoints (`/api/calculate-stream`,
which the page calls, and `/api/calculate`, its fallback) and `/api/explain`.
The calculator checks set `skip_cache`, which makes both endpoints compute a
new answer without reading or writing the 7-day cache, and the stream check
confirms that the new code computed its answer. Modal can keep sending
requests to the previous version's warm containers for a while after a
deploy, so the API names the commit a CI deploy came from on every response
(`X-ACA-API-Commit`), and each check waits until the merged commit's
containers answer it. If a
calculator check fails, the workflow rolls the app back to the previous
version.

The image installs the exact package versions in `modal-requirements.txt`,
captured from the container that served the calculator before this workflow
existed. Change a pin only with a test of the new set and a comparison of
`/api/calculate` results.

To deploy or roll back by hand (needs access to PolicyEngine's Modal
workspace):

```bash
uvx --from modal==1.4.2 modal deploy --env main modal_app.py
uvx --from modal==1.4.2 modal app history aca-calc-api --env main
uvx --from modal==1.4.2 modal app rollback aca-calc-api --env main
```

Each `/api/explain` request that misses the 7-day explanation cache calls the
Anthropic API on PolicyEngine's account.

## The frontend's host

policyengine.org serves the frontend at `/us/aca-calc` through
policyengine-app-v2's zone rewrite (`website/src/data/appZoneRoutes.ts`) to
`aca-calc.vercel.app`. `next.config.mjs` sends a visit straight to that host,
with a 308, to the same page on `www.policyengine.org/us/aca-calc`. The rule
keys on `x-forwarded-host`, which Vercel sets to the host the visitor asked
for: `aca-calc.vercel.app` on a direct visit, `www.policyengine.org` on a
request policyengine.org proxies. Previews keep their own hosts, so the rule
leaves them alone.

After a production deploy, a direct visit should answer 308 and
policyengine.org should still serve the page:

```bash
curl -sI https://aca-calc.vercel.app/us/aca-calc
curl -sI https://www.policyengine.org/us/aca-calc
```

The first should answer 308 with `location:
https://www.policyengine.org/us/aca-calc`, the second 200.

## License

Open source - see PolicyEngine US license for underlying calculations.

## Credits

Calculations powered by [PolicyEngine US](https://github.com/PolicyEngine/policyengine-us)
