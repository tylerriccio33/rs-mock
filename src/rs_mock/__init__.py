"""rs-mock: a lightweight in-process Redshift mocker built on duckdb + sqlglot."""

from rs_mock.mock import RedshiftMock, UnimplementedPostgresFeature

__all__ = ["RedshiftMock", "UnimplementedPostgresFeature"]
