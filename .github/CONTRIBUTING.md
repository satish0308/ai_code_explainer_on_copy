# Auto Code Explainer - CI/CD Guide

## Overview

This project uses GitHub Actions for CI/CD with the following workflow:

1. **Lint and Test** - Runs on every push/PR, validates code quality and runs tests
2. **Build and Publish** - Automatically publishes to PyPI on main branch commits
3. **Release** - Creates GitHub Releases automatically

## Setting Up CI/CD

### Step 1: Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add the following secrets:

| Secret Name | Description |
|-------------|-------------|
| `PYPI_API_TOKEN` | Your PyPI API token (required for publishing) |

To get a PyPI API token:
1. Go to https://pypi.org/manage/account/token/
2. Create a new API token
3. Copy it and add as `PYPI_API_TOKEN` in GitHub secrets

### Step 2: Configure Versioning

The version is controlled in `pyproject.toml`:
```toml
[tool.poetry]
version = "0.2.0"
```

Update this version before releasing new versions.

### Step 3: Trigger a Release

When you push to `main` branch, the CI/CD pipeline will:
1. Run linting and tests
2. Build the package
3. Publish to PyPI
4. Create a GitHub Release

## Manual Publishing

To manually publish:

```bash
# Configure PyPI token
poetry config pypi-token.pypi <your-pypi-token>

# Build
poetry build

# Publish
poetry publish
```

## Local Development

### Run Tests Locally

```bash
# Install dev dependencies
poetry install --with dev

# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=.

# Run specific test file
poetry run pytest tests/test_config.py
```

### Run Linters

```bash
# Lint with flake8
poetry run flake8 .

# Lint with pylint
poetry run pylint main.py config.py ai_providers.py clipboard_monitor.py ui/

# Format code with black
poetry run black .

# Sort imports with isort
poetry run isort .
```

## CI/CD Workflow Details

### lint-and-test Job
- Runs on Ubuntu latest
- Sets up Python 3.11
- Installs dependencies with Poetry
- Runs flake8 linting
- Runs pylint linting
- Runs pytest with coverage
- Uploads coverage to Codecov

### build-and-publish Job
- Runs only on main branch pushes
- Builds the package
- Publishes to PyPI using the API token

### release Job
- Creates a GitHub Release
- Uses version from pyproject.toml
- Automatically generates release notes

## Troubleshooting

### "Invalid API token" Error
- Verify your PyPI token is correct
- Check token has "Upload" permissions
- Regenerate the token if needed

### "Build failed" Error
- Check `poetry check` output locally
- Ensure all dependencies are properly specified
- Verify pyproject.toml syntax

### "Cannot find module" Error in CI
- Make sure all imports use relative imports
- Check `sys.path` handling in main.py
