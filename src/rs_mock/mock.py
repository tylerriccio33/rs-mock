"""The RedshiftMock: run Redshift SQL against an in-memory duckdb database."""

from __future__ import annotations

import duckdb
import sqlglot


class UnimplementedPostgresFeature(Exception):
    """Raised when SQL uses a PostgreSQL construct that Redshift does not support.

    Redshift excludes many PostgreSQL functions, data types, and features (see the
    AWS "Unsupported PostgreSQL ..." docs). Since this mock stands in for Redshift,
    such SQL must fail loudly here rather than silently succeed on duckdb.
    """


class RedshiftMock:
    """An in-process stand-in for Redshift.

    Redshift SQL is transpiled to duckdb via sqlglot, then executed against a
    persistent in-memory duckdb connection so state (tables, inserted rows)
    survives across `execute` calls for the lifetime of the instance.
    """

    def __init__(self) -> None:
        self._conn = duckdb.connect(":memory:")

    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        """The underlying duckdb connection, for power users."""
        return self._conn

    def execute(self, sql: str) -> duckdb.DuckDBPyConnection:
        """Transpile Redshift `sql` to duckdb and execute it.

        A single string may hold multiple statements; each is transpiled and
        run in order. Returns the duckdb cursor of the final statement, so
        callers can `.fetchall()`, `.df()`, `.arrow()`, etc.
        """
        # `transpile` splits multi-statement input and parses with the redshift
        # dialect; blank input transpiles to a single empty string, so filter
        # those out. Executing nothing is a user error.
        statements = [
            s for s in sqlglot.transpile(sql, read="redshift", write="duckdb") if s
        ]
        if not statements:
            raise ValueError("no SQL statement to execute")

        result = self._conn
        for statement in statements:
            result = self._conn.execute(statement)
        return result

    def close(self) -> None:
        """Close the underlying duckdb connection."""
        self._conn.close()
