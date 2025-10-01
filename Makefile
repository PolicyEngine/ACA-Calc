.PHONY: install test format debug clean

install:
	pip install -e ".[dev]"

test:
	uv run pytest tests/ -v

format:
	black . -l 79
	@echo "Formatting complete"

debug:
	uv run streamlit run app.py

clean:
	rm -rf __pycache__ .pytest_cache .coverage htmlcov
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
