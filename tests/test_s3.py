"""UNLOAD / COPY against a moto-mocked S3.

These exercise the full path: `rs.execute("UNLOAD ...")` serializes a query to
S3 and `rs.execute("COPY ...")` loads it back, with boto3 pointed at moto's
in-memory S3 so no real AWS is touched.
"""

from collections.abc import Iterator

import boto3
import pytest
from moto import mock_aws

from rs_mock import RedshiftMock

BUCKET = "test-bucket"


@pytest.fixture
def s3() -> Iterator[object]:
    """A moto-mocked S3 client with an empty bucket ready to use."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield client


@pytest.fixture
def rs(s3: object) -> Iterator[RedshiftMock]:
    """A RedshiftMock seeded with a `users` table, inside the mocked S3 context."""
    m = RedshiftMock()
    m.execute("CREATE TABLE users (id INT, name VARCHAR)")
    m.execute("INSERT INTO users VALUES (1, 'alice'), (2, 'bob')")
    yield m
    m.close()


def _keys(s3: object, prefix: str) -> list[str]:
    return [
        o["Key"]
        for o in s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix).get("Contents", [])
    ]


def test_unload_writes_object_to_s3(rs: RedshiftMock, s3: object) -> None:
    rs.execute(
        "UNLOAD ('select id, name from users order by id') "
        f"TO 's3://{BUCKET}/out/users_' IAM_ROLE 'arn:aws:iam::123:role/r' "
        "FORMAT AS CSV HEADER"
    )
    keys = _keys(s3, "out/")
    assert keys == ["out/users_000"]
    body = s3.get_object(Bucket=BUCKET, Key=keys[0])["Body"].read()
    assert body == b"id,name\n1,alice\n2,bob\n"


def test_unload_default_format_is_pipe_delimited_without_header(
    rs: RedshiftMock, s3: object
) -> None:
    rs.execute(
        "UNLOAD ('select id, name from users order by id') "
        f"TO 's3://{BUCKET}/raw/u_' IAM_ROLE 'arn:...'"
    )
    body = s3.get_object(Bucket=BUCKET, Key="raw/u_000")["Body"].read()
    assert body == b"1|alice\n2|bob\n"


def test_unload_transpiles_redshift_syntax_in_inner_query(
    rs: RedshiftMock, s3: object
) -> None:
    # GETDATE() is Redshift-specific and must be rewritten before duckdb runs it.
    rs.execute(
        "UNLOAD ('select GETDATE() is not null as ok') "
        f"TO 's3://{BUCKET}/g/_' IAM_ROLE 'arn:...' FORMAT AS CSV HEADER"
    )
    body = s3.get_object(Bucket=BUCKET, Key="g/_000")["Body"].read()
    assert body == b"ok\ntrue\n"


@pytest.mark.parametrize(
    "unload_opts, copy_opts",
    [
        ("FORMAT AS CSV HEADER", "FORMAT AS CSV IGNOREHEADER 1"),
        ("FORMAT AS PARQUET", "FORMAT AS PARQUET"),
        ("", ""),  # default pipe-delimited text
    ],
    ids=["csv", "parquet", "text"],
)
def test_unload_then_copy_roundtrips(
    rs: RedshiftMock, unload_opts: str, copy_opts: str
) -> None:
    rs.execute(
        "UNLOAD ('select id, name from users order by id') "
        f"TO 's3://{BUCKET}/rt/u_' IAM_ROLE 'arn:...' {unload_opts}"
    )
    rs.execute("CREATE TABLE loaded (id INT, name VARCHAR)")
    rs.execute(f"COPY loaded FROM 's3://{BUCKET}/rt/u_' IAM_ROLE 'arn:...' {copy_opts}")
    rows = rs.execute("SELECT id, name FROM loaded ORDER BY id").fetchall()
    assert rows == [(1, "alice"), (2, "bob")]


def test_copy_respects_explicit_column_list(rs: RedshiftMock, s3: object) -> None:
    s3.put_object(Bucket=BUCKET, Key="cols/f000", Body=b"bob|2\nalice|1\n")
    rs.execute("CREATE TABLE loaded (id INT, name VARCHAR)")
    # File columns are name|id; the column list maps them onto the table.
    rs.execute(f"COPY loaded (name, id) FROM 's3://{BUCKET}/cols/' IAM_ROLE 'arn:...'")
    rows = rs.execute("SELECT id, name FROM loaded ORDER BY id").fetchall()
    assert rows == [(1, "alice"), (2, "bob")]


def test_copy_concatenates_all_objects_under_prefix(
    rs: RedshiftMock, s3: object
) -> None:
    s3.put_object(Bucket=BUCKET, Key="multi/part_0", Body=b"1|alice\n")
    s3.put_object(Bucket=BUCKET, Key="multi/part_1", Body=b"2|bob\n")
    rs.execute("CREATE TABLE loaded (id INT, name VARCHAR)")
    rs.execute(f"COPY loaded FROM 's3://{BUCKET}/multi/' IAM_ROLE 'arn:...'")
    rows = rs.execute("SELECT id, name FROM loaded ORDER BY id").fetchall()
    assert rows == [(1, "alice"), (2, "bob")]


def test_copy_from_empty_prefix_loads_nothing(rs: RedshiftMock) -> None:
    rs.execute("CREATE TABLE loaded (id INT, name VARCHAR)")
    rs.execute(f"COPY loaded FROM 's3://{BUCKET}/nothing/' IAM_ROLE 'arn:...'")
    assert rs.execute("SELECT count(*) FROM loaded").fetchall() == [(0,)]
