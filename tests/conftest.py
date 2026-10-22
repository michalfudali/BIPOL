"""Shared test fixtures for BIPOL Studio E2E and unit test suites."""
import os
import tempfile
import time
from pathlib import Path
import pytest
from app import app
from calculations.trends import DATA, load_aircraft


@pytest.fixture
def client():
    """Provides a Flask test client configured in TESTING mode."""
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def isolated_db():
    """Snapshots all reference JSON files in data/aircraft/ before test and restores them on teardown.
    
    Guarantees no persistent state leakage or dataset corruption across test runs.
    """
    original_files = {}
    for p in DATA.glob("*.json"):
        if not p.name.startswith('.'):
            original_files[p.name] = p.read_bytes()
    original_names = set(original_files.keys())

    try:
        yield
    finally:
        for name, content in original_files.items():
            target = DATA / name
            if not target.exists() or target.read_bytes() != content:
                temp_fd, temp_path = tempfile.mkstemp(
                    prefix=f".restore-{target.stem}-",
                    suffix=".tmp",
                    dir=target.parent
                )
                try:
                    with os.fdopen(temp_fd, 'wb') as stream:
                        stream.write(content)
                        stream.flush()
                        os.fsync(stream.fileno())
                    for attempt in range(5):
                        try:
                            os.replace(temp_path, target)
                            break
                        except OSError:
                            if attempt == 4:
                                raise
                            time.sleep(0.025 * (2 ** attempt))
                except Exception:
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except OSError:
                            pass
                    target.write_bytes(content)

        for p in DATA.glob("*.json"):
            if p.name not in original_names and not p.name.startswith('.'):
                try:
                    p.unlink()
                except OSError:
                    pass
        load_aircraft.cache_clear()
