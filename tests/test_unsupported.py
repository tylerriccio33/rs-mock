"""Redshift excludes many PostgreSQL functions, data types, and features.

The AWS docs enumerate them:
- https://docs.aws.amazon.com/redshift/latest/dg/c_unsupported-postgresql-functions.html
- https://docs.aws.amazon.com/redshift/latest/dg/c_unsupported-postgresql-datatypes.html
- https://docs.aws.amazon.com/redshift/latest/dg/c_unsupported-postgresql-features.html

Because this mock stands in for Redshift, such SQL must raise
`UnimplementedPostgresFeature` rather than silently run on duckdb. Detection is
not yet implemented, so every case below is xfailed until it is.
"""

import pytest

from rs_mock import RedshiftMock, UnimplementedPostgresFeature


@pytest.fixture
def mock() -> RedshiftMock:
    return RedshiftMock()


# --- Unsupported functions -------------------------------------------------
UNSUPPORTED_FUNCTIONS = {
    "string_agg": "SELECT STRING_AGG(x, ',') FROM (SELECT 'a' AS x)",
    "array_agg": "SELECT ARRAY_AGG(x) FROM (SELECT 1 AS x)",
    "every": "SELECT EVERY(x > 0) FROM (SELECT 1 AS x)",
    "xml_agg": "SELECT XML_AGG(x) FROM (SELECT 'a' AS x)",
    "corr": "SELECT CORR(y, x) FROM (SELECT 1 AS x, 2 AS y)",
    "covar_pop": "SELECT COVAR_POP(y, x) FROM (SELECT 1 AS x, 2 AS y)",
    "covar_samp": "SELECT COVAR_SAMP(y, x) FROM (SELECT 1 AS x, 2 AS y)",
    "regr_avgx": "SELECT REGR_AVGX(y, x) FROM (SELECT 1 AS x, 2 AS y)",
    "regr_count": "SELECT REGR_COUNT(y, x) FROM (SELECT 1 AS x, 2 AS y)",
    "regr_intercept": "SELECT REGR_INTERCEPT(y, x) FROM (SELECT 1 AS x, 2 AS y)",
    "regr_r2": "SELECT REGR_R2(y, x) FROM (SELECT 1 AS x, 2 AS y)",
    "regr_slope": "SELECT REGR_SLOPE(y, x) FROM (SELECT 1 AS x, 2 AS y)",
    "regr_sxx": "SELECT REGR_SXX(y, x) FROM (SELECT 1 AS x, 2 AS y)",
    "clock_timestamp": "SELECT CLOCK_TIMESTAMP()",
    "justify_days": "SELECT JUSTIFY_DAYS(INTERVAL '35 days')",
    "justify_hours": "SELECT JUSTIFY_HOURS(INTERVAL '27 hours')",
    "justify_interval": "SELECT JUSTIFY_INTERVAL(INTERVAL '1 mon -1 hour')",
    "pg_sleep": "SELECT PG_SLEEP(1)",
    "transaction_timestamp": "SELECT TRANSACTION_TIMESTAMP()",
    "div": "SELECT DIV(9, 4)",
    "setseed": "SELECT SETSEED(0.5)",
    "width_bucket": "SELECT WIDTH_BUCKET(5, 0, 10, 5)",
    "generate_series": "SELECT * FROM GENERATE_SERIES(1, 5)",
    "generate_subscripts": "SELECT GENERATE_SUBSCRIPTS(ARRAY[1, 2, 3], 1)",
    "bit_length": "SELECT BIT_LENGTH('abc')",
    "overlay": "SELECT OVERLAY('Txxxxas' PLACING 'hom' FROM 2 FOR 4)",
    "convert": "SELECT CONVERT('text', 'UTF8', 'LATIN1')",
    "convert_from": "SELECT CONVERT_FROM('text', 'UTF8')",
    "convert_to": "SELECT CONVERT_TO('text', 'UTF8')",
    "encode": "SELECT ENCODE('abc', 'base64')",
    "format": "SELECT FORMAT('%s', 'x')",
    "quote_nullable": "SELECT QUOTE_NULLABLE('x')",
    "regexp_matches": "SELECT REGEXP_MATCHES('abc', 'b')",
    "regexp_split_to_array": "SELECT REGEXP_SPLIT_TO_ARRAY('a,b', ',')",
    "regexp_split_to_table": "SELECT REGEXP_SPLIT_TO_TABLE('a,b', ',')",
    "current_query": "SELECT CURRENT_QUERY()",
    "inet_client_addr": "SELECT INET_CLIENT_ADDR()",
    "pg_postmaster_start_time": "SELECT PG_POSTMASTER_START_TIME()",
    "pg_trigger_depth": "SELECT PG_TRIGGER_DEPTH()",
}


@pytest.mark.xfail(
    reason="Unsupported-function detection is not implemented", strict=True
)
@pytest.mark.parametrize(
    "sql", UNSUPPORTED_FUNCTIONS.values(), ids=UNSUPPORTED_FUNCTIONS.keys()
)
def test_unsupported_function_raises(mock: RedshiftMock, sql: str) -> None:
    with pytest.raises(UnimplementedPostgresFeature):
        mock.execute(sql)


# --- Unsupported data types ------------------------------------------------
UNSUPPORTED_DATATYPES = {
    "array": "CREATE TABLE t (c INT[])",
    "bit": "CREATE TABLE t (c BIT(8))",
    "bit_varying": "CREATE TABLE t (c BIT VARYING(8))",
    "bytea": "CREATE TABLE t (c BYTEA)",
    "enum": "CREATE TYPE mood AS ENUM ('sad', 'happy')",
    "hstore": "CREATE TABLE t (c HSTORE)",
    "json": "CREATE TABLE t (c JSON)",
    "cidr": "CREATE TABLE t (c CIDR)",
    "inet": "CREATE TABLE t (c INET)",
    "macaddr": "CREATE TABLE t (c MACADDR)",
    "serial": "CREATE TABLE t (c SERIAL)",
    "bigserial": "CREATE TABLE t (c BIGSERIAL)",
    "smallserial": "CREATE TABLE t (c SMALLSERIAL)",
    "money": "CREATE TABLE t (c MONEY)",
    "int4range": "CREATE TABLE t (c INT4RANGE)",
    "tsrange": "CREATE TABLE t (c TSRANGE)",
    "txid_snapshot": "CREATE TABLE t (c TXID_SNAPSHOT)",
    "uuid": "CREATE TABLE t (c UUID)",
    "xml": "CREATE TABLE t (c XML)",
    "tsvector": "CREATE TABLE t (c TSVECTOR)",
}


@pytest.mark.xfail(
    reason="Unsupported-data-type detection is not implemented", strict=True
)
@pytest.mark.parametrize(
    "sql", UNSUPPORTED_DATATYPES.values(), ids=UNSUPPORTED_DATATYPES.keys()
)
def test_unsupported_datatype_raises(mock: RedshiftMock, sql: str) -> None:
    with pytest.raises(UnimplementedPostgresFeature):
        mock.execute(sql)


# --- Unsupported features --------------------------------------------------
UNSUPPORTED_FEATURES = {
    "unique_constraint": "CREATE TABLE t (id INT UNIQUE)",
    "primary_key": "CREATE TABLE t (id INT PRIMARY KEY)",
    "foreign_key": "CREATE TABLE t (id INT REFERENCES other (id))",
    "check_constraint": "CREATE TABLE t (id INT CHECK (id > 0))",
    "inheritance": "CREATE TABLE child () INHERITS (parent)",
    "index": "CREATE INDEX idx ON t (id)",
    "nulls_clause_window": "SELECT LAG(id) IGNORE NULLS OVER (ORDER BY id) FROM t",
    "collation": 'CREATE TABLE t (c VARCHAR COLLATE "en_US")',
    "array_constructor": "SELECT ARRAY[1, 2, 3]",
    "row_constructor": "SELECT ROW(1, 2)",
    "trigger": "CREATE TRIGGER trg AFTER INSERT ON t EXECUTE PROCEDURE f()",
    "tablespace": "CREATE TABLESPACE ts LOCATION '/data'",
    "sequence": "CREATE SEQUENCE seq",
    "table_partitioning": "CREATE TABLE t (id INT) PARTITION BY RANGE (id)",
}


@pytest.mark.xfail(
    reason="Unsupported-feature detection is not implemented", strict=True
)
@pytest.mark.parametrize(
    "sql", UNSUPPORTED_FEATURES.values(), ids=UNSUPPORTED_FEATURES.keys()
)
def test_unsupported_feature_raises(mock: RedshiftMock, sql: str) -> None:
    with pytest.raises(UnimplementedPostgresFeature):
        mock.execute(sql)
