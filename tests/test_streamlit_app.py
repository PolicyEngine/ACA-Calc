"""Test Streamlit app execution."""
import sys
sys.path.insert(0, '.')

from streamlit.testing.v1 import AppTest


def test_app_runs():
    """Test that the app runs without errors."""
    at = AppTest.from_file("app.py")

    # Run the app
    at.run()

    # Check that there are no exceptions
    assert not at.exception, f"App raised exception: {at.exception}"

    print("✓ App loads without errors")


def test_sidebar_exists():
    """Test that sidebar is rendered."""
    at = AppTest.from_file("app.py")
    at.run()

    # Check sidebar exists
    assert len(at.sidebar) > 0, "Sidebar should exist"

    print("✓ Sidebar exists")


def test_basic_calculation():
    """Test basic calculation flow."""
    at = AppTest.from_file("app.py")
    at.run()

    # Set values in sidebar
    at.sidebar.selectbox[0].select("Single")  # Filing status
    at.sidebar.number_input[0].set_value(35)  # Age
    at.sidebar.number_input[1].set_value(0)  # Number of dependents
    at.sidebar.number_input[2].set_value(50000)  # Income
    at.sidebar.selectbox[1].select("TX")  # State

    # Click calculate button
    at.sidebar.button[0].click()
    at.run()

    # Check that results are displayed
    assert not at.exception, f"Calculation raised exception: {at.exception}"

    print("✓ Basic calculation works")


if __name__ == "__main__":
    test_app_runs()
    test_sidebar_exists()
    test_basic_calculation()
    print("\n✅ All Streamlit tests passed!")
