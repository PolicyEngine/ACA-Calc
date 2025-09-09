# Fix and Improve the ACA Premium Tax Credit Calculator

## Current Issues to Fix

The existing Streamlit app has several critical issues preventing accurate PTC calculations:

1. **County is not being used** - The app collects county input but doesn't pass it to PolicyEngine
2. **Missing PTC-specific parameters** - The simulation needs proper setup for ACA-related variables
3. **Marital status is ignored** - This affects tax unit structure and FPL calculations

## Required Fixes

### 1. Proper County Integration
- PolicyEngine needs the county to determine the correct ACA rating area
- You'll need to set the `household_county` parameter in the simulation
- The county name should match PolicyEngine's expected format (you may need to look up the correct format)

### 2. Complete PTC Calculation Setup
The simulation needs these key elements for accurate PTC calculation:
- **Tax unit structure** reflecting marital status (single vs married filing jointly)
- **Modified Adjusted Gross Income (MAGI)** for ACA purposes
- **Proper geographic identifiers** (state AND county)
- **Household members** with correct relationships (spouse, dependents)

### 3. PolicyEngine Parameter Research
Before fixing, you should:
- Check PolicyEngine documentation or source code for the exact parameter names needed:
  - How to specify county (might be `household_county`, `county_name`, or similar)
  - How to properly structure a married tax unit
  - What income variables PolicyEngine uses for PTC (likely MAGI-related)
- Test with PolicyEngine's web interface to verify your calculations match

### 4. Updated Calculation Function Structure
```python
def calculate_ptc(year, age, marital_status, income, dependent_ages, state, county):
    # Build household with proper structure
    household = {
        "people": {},
        "families": {},
        "tax_units": {},
        "households": {}
    }
    
    # Add adults based on marital status
    if marital_status == "Married filing jointly":
        # Add both spouses
        # Set up married tax unit
    else:
        # Single tax unit
    
    # Properly set geographic parameters
    # household["households"]["household"]["state_name"] = state
    # household["households"]["household"]["county"] = county  # Or whatever the correct parameter is
    
    # Ensure income is properly assigned for MAGI calculation
```

### 5. Validation Steps
Add validation to ensure accuracy:
- Print intermediate values (FPL percentage, SLCSP premium, etc.) for debugging
- Compare results with Healthcare.gov calculator for same scenarios
- Test edge cases:
  - Income at 100%, 138%, 250%, 400% FPL
  - Different family sizes
  - Different counties within same state

### 6. Additional Features to Add
- **FPL percentage display**: Show household income as % of Federal Poverty Level
- **Breakdown explanation**: Show how PTC is calculated (SLCSP - expected contribution)
- **Geographic validation**: Ensure county exists in selected state
- **Better error messages**: Specific messages for why PTC might be $0

## Implementation Priority
1. First, fix the county parameter issue
2. Then fix marital status handling  
3. Verify calculations against known examples
4. Add validation and debugging features
5. Improve user feedback and explanations

## Testing Scenarios
Test with these specific cases to verify accuracy:
- Single adult, age 35, $30,000 income, Miami-Dade County, FL
- Married couple, both age 40, $60,000 income, Cook County, IL  
- Family with 2 children, $45,000 income, Los Angeles County, CA

The results should match Healthcare.gov estimates for the same scenarios.