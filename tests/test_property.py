"""Property-based tests: invariants that should hold across many inputs."""

from hypothesis import given
from hypothesis import strategies as st
from pytest_testmap import testmap

from rs_mock import RedshiftMock


# Redshift/duckdb INT is 32-bit; keep literals in range so we test the
# roundtrip rather than integer overflow.
int32 = st.integers(min_value=-(2**31), max_value=2**31 - 1)


@testmap(feature="execute", kind="property")
@given(a=int32, b=int32)
def test_select_literals_roundtrip(a: int, b: int) -> None:
    # Whatever integers we select back out should equal what we put in.
    mock = RedshiftMock()
    try:
        rows = mock.execute(f"SELECT {a} AS a, {b} AS b").fetchall()
        assert rows == [(a, b)]
    finally:
        mock.close()


@testmap(feature="execute", kind="property")
@given(values=st.lists(int32, min_size=1, max_size=20))
def test_inserted_rows_come_back_sorted(values: list[int]) -> None:
    # Insert an arbitrary set of ints, read them back ordered, and the result
    # must match Python's own sort — the store neither drops nor mangles rows.
    mock = RedshiftMock()
    try:
        mock.execute("CREATE TABLE t (v INT)")
        literals = ", ".join(f"({v})" for v in values)
        mock.execute(f"INSERT INTO t VALUES {literals}")
        rows = mock.execute("SELECT v FROM t ORDER BY v").fetchall()
        assert [r[0] for r in rows] == sorted(values)
    finally:
        mock.close()
