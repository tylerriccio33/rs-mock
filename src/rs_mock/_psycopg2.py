"""A psycopg2-shaped adapter around `RedshiftMock`.

Wraps `RedshiftMock` in objects that quack like `psycopg2.extensions.connection`
and `psycopg2.extensions.cursor`, so code written against psycopg2 (e.g. a
`make_con` factory) can be monkeypatched to this mock without modification.
"""

from __future__ import annotations

from contextlib import ContextDecorator
from typing import Any
from unittest.mock import patch

from rs_mock.mock import RedshiftMock


class Cursor:
    """A psycopg2-cursor-shaped wrapper around a `RedshiftMock`."""

    def __init__(self, mock: RedshiftMock) -> None:
        self._mock = mock
        self._result: Any = None

    def execute(self, sql: str) -> None:
        self._result = self._mock.execute(sql)

    def fetchall(self) -> list[tuple[Any, ...]]:
        return [tuple(row) for row in self._result.fetchall()]

    @property
    def description(self) -> list[tuple[str, None, None, None, None, None, None]]:
        return [
            (col[0], None, None, None, None, None, None)
            for col in self._result.description
        ]

    def __enter__(self) -> Cursor:
        return self

    def __exit__(self, *exc_info: object) -> None:
        pass


class Connection:
    """A psycopg2-connection-shaped wrapper around a `RedshiftMock`."""

    def __init__(self) -> None:
        self._mock = RedshiftMock()
        self.closed = 0

    def cursor(self) -> Cursor:
        return Cursor(self._mock)

    def commit(self) -> None:
        """No-op: duckdb auto-commits."""

    def close(self) -> None:
        self._mock.close()
        self.closed = 1

    def __enter__(self) -> Connection:
        return self

    def __exit__(self, *exc_info: object) -> None:
        pass


class mock_psycopg2(ContextDecorator):
    """Patch `psycopg2.connect` to return an rs-mock `Connection`, mock_aws-style.

    Usable as either a context manager or a decorator:

        with mock_psycopg2():
            conn = psycopg2.connect(...)  # actually a rs_mock.Connection

        @mock_psycopg2()
        def test_something():
            conn = psycopg2.connect(...)

    Requires the `psycopg2` package to be importable (`psycopg2-binary` works).
    Only patches the `psycopg2.connect` module attribute — code that already
    holds a reference via `from psycopg2 import connect` before the patch is
    applied won't be affected, same caveat as moto's `mock_aws`.
    """

    def __init__(self) -> None:
        self._patcher: Any = None

    def __enter__(self) -> mock_psycopg2:
        import psycopg2

        self._patcher = patch.object(
            psycopg2, "connect", lambda *args, **kwargs: Connection()
        )
        self._patcher.start()
        return self

    def __exit__(self, *exc_info: object) -> bool:
        self._patcher.stop()
        return False
