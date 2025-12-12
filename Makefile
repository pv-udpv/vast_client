# Makefile for VAST Client tests

.PHONY: help test test-unit test-integration test-iab test-all benchmark coverage clean install-dev lint format type-check

# Default target
help:
	@echo "VAST Client Test Commands"
	@echo "=========================="
	@echo ""
	@echo "Testing:"
	@echo "  make test              - Run all tests"
	@echo "  make test-unit         - Run unit tests only"
	@echo "  make test-integration  - Run integration tests only"
	@echo "  make test-iab          - Run IAB samples tests only"
	@echo "  make test-fast         - Run fast tests (exclude slow)"
	@echo "  make benchmark         - Run performance benchmarks"
	@echo "  make coverage          - Run tests with coverage report"
	@echo "  make coverage-html     - Generate HTML coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint              - Run linters (ruff)"
	@echo "  make format            - Format code (black)"
	@echo "  make type-check        - Run type checker (mypy)"
	@echo "  make check-all         - Run all checks"
	@echo ""
	@echo "Development:"
	@echo "  make install-dev       - Install development dependencies"
	@echo "  make clean             - Clean test artifacts"
	@echo ""

# Install development dependencies
install-dev:
	pip install -e ".[dev,test]"

# Run all tests
test:
	pytest

# Run unit tests only
test-unit:
	pytest tests/unit/

# Run integration tests only
test-integration:
	pytest tests/integration/

# Run IAB samples tests only
test-iab:
	pytest tests/iab_samples/

# Run fast tests (exclude slow)
test-fast:
	pytest -m "not slow"

# Run all tests including slow ones
test-all:
	pytest -m ""

# Run performance benchmarks
benchmark:
	pytest -m benchmark benchmarks/multi_source_benchmarks.py -v

# Run tests with coverage
coverage:
	pytest --cov=vast_client --cov-report=term-missing

# Generate HTML coverage report
coverage-html:
	pytest --cov=vast_client --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

# Run linter
lint:
	ruff check src/vast_client tests

# Format code
format:
	black src/vast_client tests

# Type checking
type-check:
	mypy src/vast_client

# Run all quality checks
check-all: lint type-check test

# Clean test artifacts
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name .coverage -delete 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Watch mode for tests
watch:
	pytest --watch

# Run tests with verbose output
test-verbose:
	pytest -vv

# Run specific test file
test-file:
	@read -p "Enter test file path: " file; \
	pytest $$file

# Run tests matching pattern
test-pattern:
	@read -p "Enter test pattern: " pattern; \
	pytest -k "$$pattern"
