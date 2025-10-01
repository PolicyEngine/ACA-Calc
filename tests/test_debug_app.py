"""Debug Streamlit app to see what's rendering."""
import sys
sys.path.insert(0, '.')

from streamlit.testing.v1 import AppTest


def debug_app():
    """Debug what's in the app."""
    at = AppTest.from_file("app.py")
    at.run()

    print("=== APP STATE ===")
    print(f"Exception: {at.exception}")
    print(f"Main elements: {len(at.main)}")
    print(f"Sidebar elements: {len(at.sidebar)}")

    print("\n=== MAIN CONTENT ===")
    for i, element in enumerate(at.main):
        print(f"{i}: {type(element).__name__}")

    print("\n=== SIDEBAR CONTENT ===")
    for i, element in enumerate(at.sidebar):
        print(f"{i}: {type(element).__name__}")

    # Check if there are any errors in rendering
    if at.exception:
        print(f"\n=== EXCEPTION ===")
        print(at.exception)

if __name__ == "__main__":
    debug_app()
