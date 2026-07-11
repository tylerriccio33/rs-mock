# rs-mock

A super lightweight, in-process **Redshift mocker** for test suites.

rs-mock transpiles Redshift SQL to duckdb SQL with [sqlglot](https://github.com/tobymao/sqlglot)
and runs it against an in-memory [duckdb](https://duckdb.org/) database. No cluster,
no network, no Docker — just fast, in-process SQL.

## Usage

```python
from rs_mock import RedshiftMock

rs = RedshiftMock()

# DDL / DML — state persists across calls for the instance's lifetime
rs.execute("CREATE TABLE users (id INT, name VARCHAR)")
rs.execute("INSERT INTO users VALUES (1, 'alice'), (2, 'bob')")

# SELECTs, JOINs, CTEs — execute() returns the duckdb cursor
rows = rs.execute("SELECT id, name FROM users ORDER BY id").fetchall()
# [(1, 'alice'), (2, 'bob')]

# Need duckdb power features? Grab the cursor or the connection.
df = rs.execute("SELECT * FROM users").df()
rs.connection  # the underlying duckdb connection
```

Supported: regular selects, joins, CTEs, and DDL/DML. Redshift-specific syntax
(e.g. `GETDATE()`) is rewritten to its duckdb equivalent automatically.

## S3: UNLOAD and COPY

`UNLOAD` and `COPY ... FROM 's3://...'` are supported against real S3 or, in
tests, a [moto](https://github.com/getmoto/moto)-mocked bucket — no cluster and
no network. Install the extra (`pip install 'rs-mock[s3]'`) to pull in boto3,
then run UNLOAD/COPY like any other statement inside a `mock_aws` context:

```python
import boto3
from moto import mock_aws
from rs_mock import RedshiftMock

with mock_aws():
    boto3.client("s3").create_bucket(Bucket="my-bucket")

    rs = RedshiftMock()
    rs.execute("CREATE TABLE users (id INT, name VARCHAR)")
    rs.execute("INSERT INTO users VALUES (1, 'alice'), (2, 'bob')")

    # Query result -> S3 (CSV, PARQUET, JSON, or default pipe-delimited text)
    rs.execute(
        "UNLOAD ('SELECT * FROM users') TO 's3://my-bucket/users_' "
        "IAM_ROLE 'arn:aws:iam::123:role/r' FORMAT AS PARQUET"
    )

    # S3 -> table (every object under the prefix is loaded)
    rs.execute("CREATE TABLE loaded (id INT, name VARCHAR)")
    rs.execute(
        "COPY loaded FROM 's3://my-bucket/users_' "
        "IAM_ROLE 'arn:aws:iam::123:role/r' FORMAT AS PARQUET"
    )
```

Recognized options: UNLOAD `FORMAT AS {CSV|PARQUET|JSON}`, `DELIMITER`,
`HEADER`; COPY `FORMAT AS {CSV|PARQUET|JSON}`, `DELIMITER`, `IGNOREHEADER`, and a
column list. Authorization (`IAM_ROLE`/`CREDENTIALS`) is parsed but ignored —
boto3's own credential resolution (or moto) applies.

## psycopg2 compatibility

`rs_mock.Connection`/`rs_mock.Cursor` quack like `psycopg2.extensions.connection`
and `.cursor`, so code written against psycopg2 can be pointed at rs-mock with a
single monkeypatch of your connection factory:

```python
import rs_mock

def make_con():
    return rs_mock.Connection()  # instead of psycopg2.connect(...)

monkeypatch.setattr("your_module.make_con", make_con)

conn = make_con()
with conn.cursor() as cur:
    cur.execute("CREATE TABLE users (id INT, name VARCHAR)")
    cur.execute("INSERT INTO users VALUES (1, 'alice'), (2, 'bob')")
    cur.execute("SELECT * FROM users ORDER BY id")
    cur.fetchall()          # [(1, 'alice'), (2, 'bob')]
    cur.description         # [('id', None, ...), ('name', None, ...)]
conn.commit()                # no-op, duckdb auto-commits
conn.close()
```

### `mock_psycopg2`: a `mock_aws`-style decorator/context manager

If your code calls `psycopg2.connect(...)` directly (rather than going through
an injectable factory), use `mock_psycopg2` — it patches `psycopg2.connect` for
the duration of the block, exactly like moto's `mock_aws` patches boto3:

```python
from rs_mock import mock_psycopg2

@mock_psycopg2()
def test_something():
    import psycopg2

    conn = psycopg2.connect("host=localhost dbname=whatever")  # -> rs_mock.Connection
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchall()  # [(1,)]
    conn.close()

# or as a context manager
with mock_psycopg2():
    conn = psycopg2.connect(...)
    ...
```

Requires `psycopg2` (or `psycopg2-binary`) to be installed. Note this patches
the `psycopg2.connect` module attribute, so it only affects code that calls
`psycopg2.connect(...)` (or holds a reference to `psycopg2` and calls
`.connect`) *after* the patch is applied — the same caveat `mock_aws` has for
early-bound client references.

## Development

```bash
make test   # run tests
make lint   # ruff + pyrefly
make prek   # pre-commit hooks
```
