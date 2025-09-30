# Changelog

## 2025-09-29 (Evening) - Memory Optimization & Bug Fixes

### Fixed
- ✅ **Marital unit IDs** - Fixed crash with 4+ children households (in both calculate_ptc and create_chart)
- ✅ **Syntax warnings** - Removed escaped dollar signs in f-strings
- ✅ **Memory issues** - Charts now optional to prevent out-of-memory errors

### Changed
- 🔄 **Chart is now optional** - Click "📊 Show Income Comparison Chart" button to generate
- 🔄 **Chart resolution reduced** - 100 → 50 data points for lower memory usage
- ➕ **County support in charts** - Charts now use county-specific data when selected

**Memory Fix**: Chart generation consumed too much memory on free hosting tiers. Now charts are only generated on-demand when user clicks the button.

**Marital Unit Bug**: App crashed with "Unable to set value for marital_unit_id" when adding 4+ children
- **Cause**: Incorrect formula created non-sequential IDs
- **Solution**: Changed from `i + (2 if age_spouse else 1)` to `i + 1`

Verified with 1-5 children - all working correctly.

## 2025-09-29 (Afternoon) - Major Fixes & Cleanup

### Fixed
- ✅ **County support working** - All 3,143 counties now calculate correctly
- ✅ **All states functional** - Removed hardcoded Texas FIPS, each state uses proper data
- ✅ **Household structure** - Added missing `spm_units` to match PolicyEngine patterns
- ✅ **Reform logic** - IRA enhancement parameters apply correctly to 2026

### Changed
- 🔄 County parameter: `county_fips` → `county_name` (user-friendly format)
- 🔄 County format conversion: "Travis County" → "TRAVIS_COUNTY_TX" 
- 🔄 Removed state default to Travis County, TX

### Added
- ➕ Comprehensive test suite (8 test files)
- ➕ Documentation (README, CONTRIBUTING, this CHANGELOG)
- ➕ .gitignore for Python/Streamlit projects
- ➕ Error handling for missing SLCSP data

### Organized
- 📁 `tests/` - All test files
- 📁 `notebooks/` - Analysis notebooks  
- 📁 `archive/` - Historical/deprecated files
- 🗑️ Removed: `__pycache__`, unused data files

### Verified
- Texas counties show accurate variation (Travis ≠ Harris ≠ Dallas)
- NJ family saves $2,111/year with IRA extension
- 400% FPL "cliff" correctly shows $0 baseline, $2,899+ with reform
- CA, NY, FL calculations all accurate

## Previous Versions

See `archive/WORKING_STATUS.md` for debugging history.
