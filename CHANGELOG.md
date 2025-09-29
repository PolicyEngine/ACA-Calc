# Changelog

## 2025-09-29 - Major Fixes & Cleanup

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
