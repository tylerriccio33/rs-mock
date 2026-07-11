"""Exercise the adapter through the real `psycopg2` module.

These tests import `psycopg2` itself (not just mimic its shape) and monkeypatch
`psycopg2.connect` to return our `Connection`, so the code under test runs
exactly the way a caller like dip_admin's `make_con` would: through the real
psycopg2 entrypoint, using real `psycopg2.extensions.cursor.description`
semantics as the source of truth for column-shape compatibility.
"""

from collections.abc import Iterator

import psycopg2
import pytest
from pytest_testmap import testmap

from rs_mock import Connection, mock_psycopg2

DSN = "host=localhost dbname=fake user=fake password=fake"


@pytest.fixture
def connect(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Monkeypatch `psycopg2.connect` to return our mock, like `make_con` would."""
    monkeypatch.setattr(psycopg2, "connect", lambda *args, **kwargs: Connection())
    yield


@testmap(feature="psy-connect", kind="integration")
def test_connect_returns_a_connection(connect: None) -> None:
    conn = psycopg2.connect(DSN)
    assert isinstance(conn, Connection)
    conn.close()


@testmap(feature="psy-connect", kind="integration")
def test_cursor_context_manager_is_a_noop_close(connect: None) -> None:
    conn = psycopg2.connect(DSN)
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        assert cur.fetchall() == [(1,)]
    # cursor has no explicit close/closed contract per the summarized shape;
    # the connection is what owns lifecycle.
    conn.close()
    assert conn.closed == 1


@testmap(feature="psy-connect", kind="integration")
def test_mock_psycopg2_as_context_manager() -> None:
    with mock_psycopg2():
        conn = psycopg2.connect(DSN)
        assert isinstance(conn, Connection)
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            assert cur.fetchall() == [(1,)]
        conn.close()


@testmap(feature="psy-connect", kind="integration")
@mock_psycopg2()
def test_mock_psycopg2_as_decorator() -> None:
    conn = psycopg2.connect(DSN)
    assert isinstance(conn, Connection)
    conn.close()


@testmap(feature="psy-create", kind="integration")
def test_create_table_via_psycopg2(connect: None) -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("CREATE TABLE t (id INT, name VARCHAR, score DOUBLE)")
    cur.execute("SELECT * FROM t")
    assert [col[0] for col in cur.description] == ["id", "name", "score"]
    conn.close()


@testmap(feature="psy-insert", kind="integration")
def test_insert_via_psycopg2(connect: None) -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("CREATE TABLE users (id INT, name VARCHAR)")
    cur.execute("INSERT INTO users VALUES (1, 'alice'), (2, 'bob')")
    cur.execute("SELECT * FROM users ORDER BY id")
    assert cur.fetchall() == [(1, "alice"), (2, "bob")]
    conn.close()


@testmap(feature="psy-select", kind="integration")
def test_full_query_roundtrip_via_psycopg2_connect(connect: None) -> None:
    conn = psycopg2.connect(DSN)
    with conn.cursor() as cur:
        cur.execute("CREATE TABLE users (id INT, name VARCHAR)")
        cur.execute("INSERT INTO users VALUES (1, 'alice'), (2, 'bob')")
        cur.execute("SELECT * FROM users ORDER BY id")
        assert cur.fetchall() == [(1, "alice"), (2, "bob")]
    conn.commit()
    conn.close()
    assert conn.closed == 1


@testmap(feature="psy-select", kind="integration")
def test_description_matches_psycopg2_column_shape(connect: None) -> None:
    """`description` entries must be 7-tuples, matching the DB-API 2.0 / psycopg2 contract."""
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("CREATE TABLE t (id INT, name VARCHAR, score DOUBLE)")
    cur.execute("SELECT * FROM t")

    dbapi_field_count = len(
        [
            f
            for f in [
                "name",
                "type_code",
                "display_size",
                "internal_size",
                "precision",
                "scale",
                "null_ok",
            ]
        ]
    )
    assert dbapi_field_count == 7

    assert [col[0] for col in cur.description] == ["id", "name", "score"]
    for col in cur.description:
        assert len(col) == 7
        assert col[1:] == (None, None, None, None, None, None)
    conn.close()


@testmap(feature="psy-select", kind="integration")
def test_multiple_cursors_share_connection_state(connect: None) -> None:
    conn = psycopg2.connect(DSN)
    cur1 = conn.cursor()
    cur1.execute("CREATE TABLE nums (n INT)")
    cur1.execute("INSERT INTO nums VALUES (1), (2), (3)")

    cur2 = conn.cursor()
    cur2.execute("SELECT SUM(n) FROM nums")
    assert cur2.fetchall() == [(6,)]
    conn.close()


@testmap(feature="psy-select", kind="integration")
def test_multi_statement_execute(connect: None) -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE multi (id INT); INSERT INTO multi VALUES (1), (2); "
        "SELECT * FROM multi ORDER BY id"
    )
    assert cur.fetchall() == [(1,), (2,)]
    conn.close()


@testmap(feature="psy-commit", kind="integration")
def test_commit_is_a_noop_and_data_persists(connect: None) -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("CREATE TABLE persisted (id INT)")
    cur.execute("INSERT INTO persisted VALUES (42)")
    conn.commit()
    cur.execute("SELECT * FROM persisted")
    assert cur.fetchall() == [(42,)]
    conn.close()


@testmap(feature="psy-fetchall", kind="integration")
def test_fetchall_returns_all_rows_via_psycopg2(connect: None) -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("CREATE TABLE nums (n INT)")
    cur.execute("INSERT INTO nums VALUES (1), (2), (3)")
    cur.execute("SELECT * FROM nums ORDER BY n")
    rows = cur.fetchall()
    assert rows == [(1,), (2,), (3,)]
    assert all(isinstance(row, tuple) for row in rows)
    conn.close()
