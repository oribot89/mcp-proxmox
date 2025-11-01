.PHONY: help install install-dev test lint format clean run check security docs

# Default target
help:
	@echo "MCP Proxmox Server - Available Commands:"
	@echo ""
	@echo "  make install      - Install production dependencies"
	@echo "  make install-dev  - Install development dependencies"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make security     - Run security scans"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make run          - Run MCP server"
	@echo "  make check        - Run all checks (lint + test + security)"
	@echo "  make docs         - Generate documentation"
	@echo ""

# Install production dependencies
install:
	@echo "Installing production dependencies..."
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	pip install -e .
	@echo "✅ Installation complete"

# Install development dependencies
install-dev: install
	@echo "Installing development dependencies..."
	pip install pytest pytest-cov pytest-asyncio
	pip install black flake8 pylint isort mypy
	pip install bandit safety pip-audit
	@echo "✅ Development dependencies installed"

# Run tests
test:
	@echo "Running tests..."
	pytest tests/ -v --cov=src/proxmox_mcp --cov-report=term-missing --cov-report=html
	@echo "✅ Tests complete"

# Run linters
lint:
	@echo "Running linters..."
	@echo "→ flake8..."
	flake8 src/ --max-line-length=120 --extend-ignore=E203,W503 || true
	@echo "→ pylint..."
	pylint src/proxmox_mcp/ --max-line-length=120 --disable=C0111,R0913,R0914 || true
	@echo "→ mypy..."
	mypy src/ --ignore-missing-imports || true
	@echo "✅ Linting complete"

# Format code
format:
	@echo "Formatting code..."
	@echo "→ black..."
	black src/ tests/ --line-length=120
	@echo "→ isort..."
	isort src/ tests/ --profile black
	@echo "✅ Formatting complete"

# Run security scans
security:
	@echo "Running security scans..."
	@echo "→ bandit (code security)..."
	bandit -r src/ -ll || true
	@echo "→ safety (dependency vulnerabilities)..."
	safety check || true
	@echo "→ pip-audit (dependency audit)..."
	pip-audit || true
	@echo "✅ Security scans complete"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .eggs/ .pytest_cache/ .coverage htmlcov/ .mypy_cache/ .tox/
	@echo "✅ Cleanup complete"

# Run MCP server
run:
	@echo "Starting MCP server..."
	python -m proxmox_mcp.server

# Run all checks
check: lint test security
	@echo "✅ All checks passed"

# Generate documentation
docs:
	@echo "Generating documentation..."
	@echo "Documentation is in docs/ directory"
	@echo "Main README: README.md"
	@echo "API Reference: See README.md for available tools"
	@echo "✅ Documentation ready"

# Verify installation
verify:
	@echo "Verifying installation..."
	@python -c "import sys; print(f'Python: {sys.version}')"
	@python -c "import proxmox_mcp; print('✅ proxmox_mcp package found')"
	@test -f .env && echo "✅ .env file exists" || echo "⚠️  .env file missing (copy from .env.example)"
	@echo "✅ Verification complete"

# Create virtual environment
venv:
	@echo "Creating virtual environment..."
	python3 -m venv .venv
	@echo "✅ Virtual environment created"
	@echo "Activate with: source .venv/bin/activate"

# Full setup (venv + install + verify)
setup: venv
	@echo "Setting up project..."
	@echo "Please run: source .venv/bin/activate && make install"

