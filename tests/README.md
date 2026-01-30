# Testing Guide

## Running Tests

### All Tests
```bash
# Run all tests with Django's test runner
python manage.py test

# Run all tests with pytest
pytest
```

### Integration Tests Only
```bash
# Using Django test runner
python manage.py test tests.integration

# Using pytest with markers
pytest -m integration
```

### Multi-Database Testing

#### SQLite (Default)
```bash
# Django
python manage.py test tests.integration.test_persistence_django

# Pytest
pytest tests/integration/ --db=sqlite
```

#### MongoDB
```bash
# Ensure MongoDB is running (docker-compose up -d mongo)

# Django with environment variable
$env:OPENANOMALY_DATABASE_TYPE='mongodb'
python manage.py test tests.integration.test_persistence_django

# Pytest with command-line option
pytest tests/integration/ --db=mongodb
```

#### Both Databases (Automated)
```bash
# Using tox (recommended for CI/CD)
tox

# Or run both manually
pytest tests/integration/ --db=sqlite
pytest tests/integration/ --db=mongodb
```

## Test Organization

```
tests/
├── conftest.py              # Pytest configuration & fixtures
├── README.md                # This file
├── integration/
│   ├── __init__.py
│   └── test_persistence_django.py  # Multi-DB persistence tests
└── unit/                    # Future unit tests
```

## Test Markers

- `@pytest.mark.integration` - Tests requiring database access
- `@pytest.mark.sqlite` - SQLite-specific tests
- `@pytest.mark.mongodb` - MongoDB-specific tests
- `@pytest.mark.slow` - Long-running tests

### Running Specific Markers
```bash
pytest -m "integration and not slow"
pytest -m mongodb
```

## Continuous Integration

The `tox.ini` configuration runs tests against both databases automatically:

```bash
tox           # Run all test environments
tox -e py314-sqlite   # SQLite only
tox -e py314-mongodb  # MongoDB only
```

## Writing New Tests

### Django TestCase
```python
import pytest
from django.test import TransactionTestCase

@pytest.mark.integration
class MyIntegrationTest(TransactionTestCase):
    def test_something(self):
        # Your test here
        pass
```

### Pytest Style (Alternative)
```python
import pytest

@pytest.mark.integration
def test_my_feature(db):
    # Your test here
    pass
```
