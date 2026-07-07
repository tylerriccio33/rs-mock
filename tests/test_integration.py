"""Integration tests: end-to-end Redshift SQL transpiled and run on duckdb."""

from rs_mock import RedshiftMock


def test_regular_select(mock: RedshiftMock) -> None:
    rows = mock.execute("SELECT 1 AS a, 2 AS b").fetchall()
    assert rows == [(1, 2)]


def test_ddl_and_dml_persist_across_calls(mock: RedshiftMock) -> None:
    mock.execute("CREATE TABLE t (id INT, name VARCHAR)")
    mock.execute("INSERT INTO t VALUES (1, 'alice'), (2, 'bob')")
    rows = mock.execute("SELECT id, name FROM t ORDER BY id").fetchall()
    assert rows == [(1, "alice"), (2, "bob")]


def test_join(mock: RedshiftMock) -> None:
    mock.execute("CREATE TABLE a (id INT, val INT)")
    mock.execute("CREATE TABLE b (id INT, tag VARCHAR)")
    mock.execute("INSERT INTO a VALUES (1, 10), (2, 20)")
    mock.execute("INSERT INTO b VALUES (1, 'x'), (2, 'y')")
    rows = mock.execute(
        "SELECT a.val, b.tag FROM a JOIN b ON a.id = b.id ORDER BY a.id"
    ).fetchall()
    assert rows == [(10, "x"), (20, "y")]


def test_cte(mock: RedshiftMock) -> None:
    rows = mock.execute(
        "WITH nums AS (SELECT 1 AS n UNION ALL SELECT 2) SELECT SUM(n) FROM nums"
    ).fetchall()
    assert rows == [(3,)]


def test_multiple_statements_in_one_call(mock: RedshiftMock) -> None:
    rows = mock.execute(
        "CREATE TABLE t (id INT); INSERT INTO t VALUES (7); SELECT id FROM t"
    ).fetchall()
    assert rows == [(7,)]


def test_redshift_specific_syntax_is_transpiled(mock: RedshiftMock) -> None:
    # GETDATE() is Redshift-specific; it must be rewritten for duckdb.
    rows = mock.execute("SELECT GETDATE() IS NOT NULL AS ok").fetchall()
    assert rows == [(True,)]
