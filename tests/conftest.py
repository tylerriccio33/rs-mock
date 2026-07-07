"""Shared fixtures for the test suite."""

from collections.abc import Iterator

import pytest

from rs_mock import RedshiftMock


@pytest.fixture
def mock() -> Iterator[RedshiftMock]:
    """A fresh RedshiftMock backed by its own in-memory duckdb connection."""
    m = RedshiftMock()
    yield m
    m.close()
