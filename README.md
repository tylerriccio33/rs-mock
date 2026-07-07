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

## Development

```bash
make test   # run tests
make lint   # ruff + pyrefly
make prek   # pre-commit hooks
```
