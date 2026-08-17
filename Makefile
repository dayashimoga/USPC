.PHONY: help install-dev test test-unit test-media test-security coverage lint format clean doctor build-media

PYTHON ?= python
PIP ?= pip
PYTEST ?= pytest
RUFF ?= ruff

help:
	@echo "Universal Personal Cloud Platform (USPC)"
	@echo "=========================================="
	@echo "Available targets:"
	@echo "  install-dev    Install development dependencies in editable mode"
	@echo "  test           Run full automated test suite"
	@echo "  test-unit      Run unit tests"
	@echo "  test-media     Run media processing & streaming tests"
	@echo "  test-security  Run security validation tests"
	@echo "  coverage       Run test suite with code coverage analysis (>90% requirement)"
	@echo "  lint           Run linter (ruff)"
	@echo "  format         Auto-format code"
	@echo "  clean          Remove temporary files and build artifacts"

install-dev:
	$(PIP) install -e ".[dev]"

test:
	$(PYTHON) -m pytest tests/

test-unit:
	$(PYTHON) -m pytest tests/unit/

test-media:
	$(PYTHON) -m pytest tests/media/

test-security:
	$(PYTHON) -m pytest tests/security/

coverage:
	$(PYTHON) -m pytest --cov=src --cov-report=term-missing --cov-report=html tests/

lint:
	$(PYTHON) -m ruff check src/ tests/

format:
	$(PYTHON) -m ruff format src/ tests/

clean:
	rm -rf build/ dist/ *.egg-info .coverage htmlcov/ .pytest_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
