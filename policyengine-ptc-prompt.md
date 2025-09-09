# Build a Streamlit App to Calculate ACA Premium Tax Credit Changes

## Project Overview
Create a Streamlit web application that uses PolicyEngine US to calculate and compare a household's ACA Premium Tax Credit (PTC) for 2025 (with enhanced credits) versus 2026 (after enhanced credits expire).

## Core Requirements

### 1. User Input Collection
The app should collect the following household information through Streamlit input widgets:
- **Head of household details:**
  - Age (numeric input)
  - Marital status (selectbox: Single, Married filing jointly, etc.)
  - Annual income (numeric input)
- **Dependents:**
  - Number of dependents (numeric input)
  - Age of each dependent (dynamic inputs based on number)
- **Location:**
  - State (selectbox)
  - County (selectbox - dynamically filtered based on state selection)
  - Copy some of this from the PolicyEngine app if needed

### 2. PolicyEngine Integration
- Use `policyengine-us` package to calculate Premium Tax Credit
- Create two separate calculations:
  - 2025 scenario (with enhanced PTC from IRA)
  - 2026 scenario (after enhanced PTC expires)
- The policy already includes the expiration logic, so just changing the year should handle this

### 3. Results Display
Show a comparison dashboard with:
- **2025 PTC amount**
- **2026 PTC amount**
- **Difference in dollars and percentage**
- **Clear indicator if household loses ALL PTC eligibility in 2026**
- Visual comparison (consider using a bar chart or similar)

### 4. Technical Specifications
- Use Streamlit for the web interface
- Use PolicyEngine US for calculations
- Handle edge cases:
  - Households that lose complete PTC eligibility
  - Invalid inputs
  - Missing county/state combinations

### 5. User Experience
- Clear, intuitive layout
- Help text explaining what PTC is and why it's changing
- Real-time updates when inputs change
- Professional styling with Streamlit's layout options

## Implementation Notes

1. **ACA Rating Areas**: The county selection is crucial because ACA premium tax credits are calculated based on local benchmark plans in each rating area

2. **Key PolicyEngine Parameters**:
   - Set up household structure with adults and dependents
   - Include state and county for proper geographic calculations
   - Ensure income is properly formatted for PolicyEngine

3. **Display Requirements**:
   - Format dollar amounts with proper currency formatting
   - Use colors to highlight significant changes (e.g., red for losses)
   - Include a summary statement about the impact

## Example Code Structure
```python
import streamlit as st
from policyengine_us import Simulation

# Title and description
st.title("ACA Premium Tax Credit Calculator")
st.markdown("Compare your premium tax credits before and after enhanced credits expire")

# Input section
with st.form("household_info"):
    # Collect all inputs
    # ...
    
# Calculate using PolicyEngine
def calculate_ptc(year, household_params):
    # Create simulation
    # Return PTC amount
    pass

# Display results
# ...
```

## Success Criteria
- Accurately calculates PTC for both years using PolicyEngine
- Clearly shows the financial impact of enhanced credit expiration
- Handles all edge cases gracefully
- Provides an intuitive, professional user interface
- Explicitly identifies households that lose all PTC eligibility