"""Test that app imports and basic functions work."""
import sys
sys.path.insert(0, '.')


def test_app_imports():
    """Test that the app module can be imported without errors."""
    try:
        import app
        assert hasattr(app, 'main')
        assert hasattr(app, 'calculate_ptc')
        assert hasattr(app, 'get_fpl')
        assert hasattr(app, 'COLORS')
    except Exception as e:
        raise AssertionError(f"Failed to import app: {e}")


def test_colors_defined():
    """Test that color palette is properly defined."""
    import app
    assert 'primary' in app.COLORS
    assert 'gray' in app.COLORS
    assert 'green' in app.COLORS
    assert app.COLORS['primary'] == '#2C6496'
    assert app.COLORS['gray'] == '#808080'


def test_fpl_calculation():
    """Test Federal Poverty Level calculation."""
    import app

    # Test known FPL values for 2026
    assert app.get_fpl(1) == 15570
    assert app.get_fpl(2) == 21130
    assert app.get_fpl(4) == 32200

    # Test that it increases for larger households
    assert app.get_fpl(9) > app.get_fpl(8)


def test_fpl_percentage():
    """Test FPL percentage calculation."""
    import app

    # Single person at 100% FPL
    pct = app.calculate_fpl_percentage(15570, 1)
    assert pct == 100.0

    # Family of 4 at 300% FPL
    income = 32200 * 3
    pct = app.calculate_fpl_percentage(income, 4)
    assert 299 < pct < 301  # Allow for rounding


if __name__ == "__main__":
    test_app_imports()
    test_colors_defined()
    test_fpl_calculation()
    test_fpl_percentage()
    print("✓ All tests passed!")
