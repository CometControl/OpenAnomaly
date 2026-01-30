"""
Pytest configuration for OpenAnomaly integration tests.
"""
import os
import pytest
from django.core.management import call_command


def pytest_addoption(parser):
    """Add custom command line options for database selection."""
    parser.addoption(
        "--db",
        action="store",
        default="sqlite",
        choices=["sqlite", "mongodb"],
        help="Database backend to test against: sqlite or mongodb"
    )


@pytest.fixture(scope="session", autouse=True)
def django_db_setup_custom(request, django_db_blocker):
    """Configure Django database based on --db option."""
    db_type = request.config.getoption("--db")
    os.environ["OPENANOMALY_DATABASE_TYPE"] = db_type
    
    # Ensure Django settings are configured with the correct DB type
    from django.conf import settings
    settings.DATABASE_TYPE = db_type
    
    # Let pytest-django handle the database creation
    with django_db_blocker.unblock():
        # Migrations are applied automatically by pytest-django
        pass


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all tests automatically."""
    pass
