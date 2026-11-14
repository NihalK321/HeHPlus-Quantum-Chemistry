"""Keep backend test databases independent of shared Windows temp permissions."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest


@pytest.fixture
def tmp_path():
    """Give each test a unique, automatically cleaned project-local folder.

    This overrides pytest's default tmp_path fixture only for backend tests.
    No shared pytest-of-<user> directory or Windows permission changes are needed.
    """
    with TemporaryDirectory(prefix=".test-tmp-", dir=Path(__file__).resolve().parent) as directory:
        yield Path(directory)
