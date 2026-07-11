"""rs-mock: a lightweight in-process Redshift mocker built on duckdb + sqlglot."""

from rs_mock._psycopg2 import Connection, Cursor, mock_psycopg2
from rs_mock.mock import RedshiftMock, UnimplementedPostgresFeature

__all__ = [
    "Connection",
    "Cursor",
    "RedshiftMock",
    "UnimplementedPostgresFeature",
    "mock_psycopg2",
]
