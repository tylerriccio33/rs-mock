"""Unit tests for the psycopg2-shaped `Connection`/`Cursor` adapter itself."""

from collections.abc import Iterator

import pytest
from pytest_testmap import testmap

from rs_mock import Connection


@pytest.fixture
def conn() -> Iterator[Connection]:
    c = Connection()
    yield c
    c.close()


@testmap(feature="psy-connect", kind="unit")
def test_connection_starts_open(conn: Connection) -> None:
    assert conn.closed == 0


@testmap(feature="psy-connect", kind="unit")
def test_close_sets_closed_flag(conn: Connection) -> None:
    conn.close()
    assert conn.closed == 1


@testmap(feature="psy-connect", kind="unit")
def test_connection_is_a_context_manager(conn: Connection) -> None:
    with conn as entered:
        assert entered is conn


@testmap(feature="psy-connect", kind="unit")
def test_cursor_is_a_context_manager(conn: Connection) -> None:
    cur = conn.cursor()
    with cur as entered:
        assert entered is cur


@testmap(feature="psy-create", kind="unit")
def test_create_table_executes_without_error(conn: Connection) -> None:
    cur = conn.cursor()
    cur.execute("CREATE TABLE widgets (id INT, name VARCHAR)")
    cur.execute("SELECT * FROM widgets")
    assert cur.fetchall() == []


@testmap(feature="psy-insert", kind="unit")
def test_insert_then_select_returns_row(conn: Connection) -> None:
    cur = conn.cursor()
    cur.execute("CREATE TABLE widgets (id INT, name VARCHAR)")
    cur.execute("INSERT INTO widgets VALUES (1, 'gear')")
    cur.execute("SELECT * FROM widgets")
    assert cur.fetchall() == [(1, "gear")]


@testmap(feature="psy-select", kind="unit")
def test_cursor_description_shape(conn: Connection) -> None:
    cur = conn.cursor()
    cur.execute("SELECT 1 AS a")
    assert cur.description == [("a", None, None, None, None, None, None)]


@testmap(feature="psy-select", kind="unit")
def test_select_with_where_clause_filters_rows(conn: Connection) -> None:
    cur = conn.cursor()
    cur.execute("CREATE TABLE nums (n INT)")
    cur.execute("INSERT INTO nums VALUES (1), (2), (3)")
    cur.execute("SELECT * FROM nums WHERE n > 1 ORDER BY n")
    assert cur.fetchall() == [(2,), (3,)]


@testmap(feature="psy-commit", kind="unit")
def test_commit_is_a_noop(conn: Connection) -> None:
    assert conn.commit() is None


@testmap(feature="psy-fetchall", kind="unit")
def test_cursor_fetchall_returns_tuples(conn: Connection) -> None:
    cur = conn.cursor()
    cur.execute("SELECT 1 AS a, 2 AS b")
    rows = cur.fetchall()
    assert rows == [(1, 2)]
    assert all(isinstance(row, tuple) for row in rows)


@testmap(feature="psy-fetchall", kind="unit")
def test_cursor_fetchall_returns_multiple_rows(conn: Connection) -> None:
    cur = conn.cursor()
    cur.execute("CREATE TABLE nums (n INT)")
    cur.execute("INSERT INTO nums VALUES (1), (2), (3)")
    cur.execute("SELECT * FROM nums ORDER BY n")
    assert cur.fetchall() == [(1,), (2,), (3,)]
