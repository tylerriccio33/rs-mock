"""Unit tests: RedshiftMock's own behavior in isolation from real SQL work.

These focus on the class contract — transpilation wiring, statement splitting,
input validation, lifecycle — rather than the correctness of any given query.
"""

import duckdb
import pytest
from pytest_testmap import testmap

from rs_mock import RedshiftMock


@testmap(feature="execute", kind="unit")
def test_connection_property_exposes_duckdb_connection(mock: RedshiftMock) -> None:
    assert isinstance(mock.connection, duckdb.DuckDBPyConnection)


@testmap(feature="execute", kind="unit")
def test_execute_returns_a_cursor(mock: RedshiftMock) -> None:
    result = mock.execute("SELECT 1")
    assert isinstance(result, duckdb.DuckDBPyConnection)


@testmap(feature="execute", kind="unit")
def test_empty_sql_raises(mock: RedshiftMock) -> None:
    with pytest.raises(ValueError):
        mock.execute("")


@testmap(feature="execute", kind="unit")
def test_whitespace_only_sql_raises(mock: RedshiftMock) -> None:
    with pytest.raises(ValueError):
        mock.execute("   \n\t  ")


@testmap(feature="execute", kind="unit")
def test_execute_returns_cursor_of_final_statement(mock: RedshiftMock) -> None:
    # Multiple statements in one call: the returned cursor is the last one.
    rows = mock.execute("SELECT 1 AS a; SELECT 2 AS b").fetchall()
    assert rows == [(2,)]


@testmap(feature="execute", kind="unit")
def test_close_makes_connection_unusable(mock: RedshiftMock) -> None:
    mock.close()
    with pytest.raises(duckdb.ConnectionException):
        mock.execute("SELECT 1")
