"""The RedshiftMock: run Redshift SQL against an in-memory duckdb database."""

from __future__ import annotations

import duckdb
import sqlglot
from sqlglot import expressions as exp

from rs_mock import _s3


class UnimplementedPostgresFeature(Exception):
    """Raised when SQL uses a PostgreSQL construct that Redshift does not support.

    Redshift excludes many PostgreSQL functions, data types, and features (see the
    AWS "Unsupported PostgreSQL ..." docs). Since this mock stands in for Redshift,
    such SQL must fail loudly here rather than silently succeed on duckdb.
    """


def _is_unload(statement: exp.Expression) -> bool:
    """True if `statement` is an UNLOAD, which sqlglot leaves as a raw Command."""
    return isinstance(statement, exp.Command) and statement.name.upper() == "UNLOAD"


def _unload_text(statement: exp.Command) -> str:
    """Reconstruct an UNLOAD's original text from its Command node.

    sqlglot does not model UNLOAD; it stores the keyword in `name` and the raw
    remainder ("('query') TO '...' ...") verbatim in the string expression, so
    stitching them back yields the source `_s3.parse_unload` expects.
    """
    remainder = statement.expression.this if statement.expression else ""
    return f"UNLOAD {remainder}"


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
        run in order. `UNLOAD` and `COPY ... FROM 's3://...'` are intercepted and
        run against S3 via boto3 (see `rs_mock._s3`) rather than transpiled.
        Returns the duckdb cursor of the final statement, so callers can
        `.fetchall()`, `.df()`, `.arrow()`, etc.
        """
        # `parse` splits multi-statement input with the redshift dialect; blank
        # input parses to a single `None`, so filter those out. Executing
        # nothing is a user error.
        statements = [s for s in sqlglot.parse(sql, read="redshift") if s]
        if not statements:
            raise ValueError("no SQL statement to execute")

        result = self._conn
        for statement in statements:
            if _is_unload(statement):
                _s3.run_unload(self._conn, _unload_text(statement))
            elif _s3.is_s3_copy(statement):
                _s3.run_copy(self._conn, statement)
            else:
                result = self._conn.execute(statement.sql(dialect="duckdb"))
        return result

    def close(self) -> None:
        """Close the underlying duckdb connection."""
        self._conn.close()
