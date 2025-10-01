"""Show actual errors in the app."""
import sys
sys.path.insert(0, '.')

from streamlit.testing.v1 import AppTest


def show_errors():
    """Show errors in the app."""
    at = AppTest.from_file("app.py")
    at.run()

    print("=== ERRORS ===")
    for element in at.main:
        if hasattr(element, 'value') and 'Error' in str(type(element).__name__):
            print(f"Error: {element.value}")
        if hasattr(element, 'body'):
            print(f"Body: {element.body}")

    # Try to access error blocks differently
    errors = [e for e in at.main if 'Error' in str(type(e).__name__)]
    print(f"\nFound {len(errors)} errors")

    for i, error in enumerate(errors):
        print(f"\nError {i+1}:")
        print(dir(error))
        if hasattr(error, 'value'):
            print(f"  Value: {error.value}")
        if hasattr(error, 'message'):
            print(f"  Message: {error.message}")
        if hasattr(error, 'icon'):
            print(f"  Icon: {error.icon}")

if __name__ == "__main__":
    show_errors()
