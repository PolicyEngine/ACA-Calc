"""Test that all plotly_chart elements have unique keys."""

import re


def test_all_plotly_charts_have_unique_keys():
    """Verify all st.plotly_chart calls have unique key parameters."""
    with open("app.py", "r") as f:
        content = f.read()

    # Find all st.plotly_chart calls
    # Pattern matches: st.plotly_chart(...) including multiline
    pattern = r'st\.plotly_chart\([^)]+(?:\n[^)]+)*\)'
    matches = re.findall(pattern, content)

    print(f"\nFound {len(matches)} st.plotly_chart calls")

    keys = []
    missing_keys = []

    for i, match in enumerate(matches):
        # Look for key= parameter
        key_match = re.search(r'key\s*=\s*["\']([^"\']+)["\']', match)
        if key_match:
            key = key_match.group(1)
            keys.append(key)
            print(f"  Chart {i+1}: key='{key}'")
        else:
            missing_keys.append(i+1)
            print(f"  Chart {i+1}: ⚠️  NO KEY")

    # Assert all charts have keys
    assert len(missing_keys) == 0, f"Charts missing keys: {missing_keys}"

    # Assert all keys are unique
    duplicate_keys = [k for k in keys if keys.count(k) > 1]
    assert len(duplicate_keys) == 0, f"Duplicate keys found: {set(duplicate_keys)}"

    print(f"\n✓ All {len(matches)} charts have unique keys")


if __name__ == "__main__":
    test_all_plotly_charts_have_unique_keys()
