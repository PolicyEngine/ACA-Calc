import pandas as pd
import json

# Fetch the CSV from PolicyEngine
url = "https://raw.githubusercontent.com/PolicyEngine/policyengine-us/master/policyengine_us/parameters/gov/hhs/medicaid/geography/aca_rating_areas.csv"
df = pd.read_csv(url)

# Process counties
counties_by_state = {}

for county_full in df['county'].unique():
    if county_full == 'county':  # Skip header if present
        continue
    
    # Extract state abbreviation (last 2 chars)
    state = county_full[-2:]
    
    # Extract county name (everything before _STATE)
    county_name = county_full[:-3]  # Remove _ST
    
    # Convert from UPPER_CASE to Title Case
    county_name = county_name.replace('_', ' ').title()
    
    # Fix special cases
    county_name = county_name.replace(' County ', ' County ')
    county_name = county_name.replace(' St ', ' St. ')
    
    if state not in counties_by_state:
        counties_by_state[state] = []
    
    if county_name not in counties_by_state[state]:
        counties_by_state[state].append(county_name)

# Sort counties within each state
for state in counties_by_state:
    counties_by_state[state].sort()

# Save to file
with open('counties.json', 'w') as f:
    json.dump(counties_by_state, f, indent=2)

print(f"Processed {len(counties_by_state)} states")
for state, counties in list(counties_by_state.items())[:3]:
    print(f"{state}: {len(counties)} counties - {', '.join(counties[:3])}...")