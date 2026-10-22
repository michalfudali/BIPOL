"""Shared test fixtures for BIPOL Studio E2E and unit test suites."""
import atexit
import os
import shutil
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

import pytest

from calculations import aircraft_store

# Tests never write to the committed catalogue. They use a private copy, set before the
# application is imported; subprocesses inherit it through the environment variable.
_TEST_DIR = Path(tempfile.mkdtemp(prefix='bipol-aircraft-'))
PRISTINE_DB = _TEST_DIR / 'pristine.sqlite3'
TEST_DB = _TEST_DIR / 'aircraft.sqlite3'
shutil.copyfile(aircraft_store.DEFAULT_PATH, PRISTINE_DB)
shutil.copyfile(PRISTINE_DB, TEST_DB)
os.environ['BIPOL_AIRCRAFT_DB'] = str(TEST_DB)
atexit.register(shutil.rmtree, _TEST_DIR, ignore_errors=True)

from app import app  # noqa: E402
from calculations.trends import load_aircraft  # noqa: E402


def restore_test_database():
    """Copy the pristine catalogue into the test database through SQLite (safe with open readers)."""
    with closing(sqlite3.connect(PRISTINE_DB)) as source, closing(sqlite3.connect(TEST_DB, timeout=30)) as target:
        source.backup(target)
    load_aircraft.cache_clear()


@pytest.fixture
def client():
    """Provides a Flask test client configured in TESTING mode."""
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def isolated_db():
    """Restores the test catalogue after the test, whatever the test changed."""
    try:
        yield
    finally:
        restore_test_database()
