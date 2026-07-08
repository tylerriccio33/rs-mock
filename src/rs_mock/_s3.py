"""S3-backed UNLOAD and COPY support for RedshiftMock.

Redshift's ``UNLOAD`` and ``COPY`` move data between the cluster and Amazon S3.
This module reproduces that against whatever S3 ``boto3`` can see. In tests that
is typically a `moto <https://github.com/getmoto/moto>`_-mocked bucket, so a plain
``rs.execute("UNLOAD ...")`` / ``rs.execute("COPY ...")`` works inside a
``@mock_aws`` context with no real network, credentials, or cluster.

The data itself is (de)serialized by duckdb: UNLOAD runs the inner query and
writes the result to a temp file with duckdb's ``COPY ... TO``, then uploads the
bytes; COPY downloads the object(s) under the prefix and reads them back with
``read_csv``/``read_parquet``/``read_json_auto`` before inserting into the table.
"""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import sqlglot
from sqlglot import expressions as exp

if TYPE_CHECKING:
    import duckdb


def _s3_client() -> object:
    """A boto3 S3 client, imported lazily so boto3 stays an optional extra.

    Inside a moto ``@mock_aws`` context this client transparently talks to the
    mocked S3; outside one it hits real AWS.
    """
    try:
        import boto3
    except ModuleNotFoundError as e:  # pragma: no cover - exercised via message
        raise ModuleNotFoundError(
            "UNLOAD/COPY need boto3. Install the S3 extra: pip install 'rs-mock[s3]'."
        ) from e
    return boto3.client("s3")


def _split_s3_uri(uri: str) -> tuple[str, str]:
    """Split ``s3://bucket/some/key`` into ``("bucket", "some/key")``."""
    m = re.fullmatch(r"s3://([^/]+)/(.*)", uri, re.IGNORECASE | re.DOTALL)
    if not m:
        raise ValueError(f"not an S3 URI: {uri!r}")
    return m.group(1), m.group(2)


@dataclass(frozen=True)
class _Format:
    """The resolved on-disk format for an UNLOAD/COPY.

    ``kind`` is one of ``CSV``, ``TEXT`` (delimited, Redshift's default),
    ``PARQUET`` or ``JSON``. ``header`` means "write a header row" for UNLOAD and
    "the file has a header row to skip" for COPY.
    """

    kind: str
    delimiter: str
    header: bool

    def write_options(self) -> str:
        """duckdb ``COPY ... TO (<here>)`` options for writing this format."""
        if self.kind == "PARQUET":
            return "FORMAT PARQUET"
        if self.kind == "JSON":
            return "FORMAT JSON"
        # duckdb's CSV writer defaults HEADER on; Redshift only writes one when
        # asked, so state it explicitly either way.
        header = "true" if self.header else "false"
        return f"FORMAT CSV, DELIMITER '{_sql_quote(self.delimiter)}', HEADER {header}"

    def read_expr(self, path: Path) -> str:
        """A duckdb table function that reads a file written in this format."""
        p = _sql_quote(str(path))
        if self.kind == "PARQUET":
            return f"read_parquet('{p}')"
        if self.kind == "JSON":
            return f"read_json_auto('{p}')"
        header = "true" if self.header else "false"
        return f"read_csv('{p}', delim='{_sql_quote(self.delimiter)}', header={header})"


def _sql_quote(value: str) -> str:
    """Escape a value for embedding inside a single-quoted SQL string."""
    return value.replace("'", "''")


# --- UNLOAD ---------------------------------------------------------------

# UNLOAD ('<query>') TO '<target>' ... — inner single quotes are doubled, so the
# capture allows either a non-quote char or an escaped '' pair.
_UNLOAD_QUERY = re.compile(
    r"UNLOAD\s*\(\s*'((?:[^']|'')*)'\s*\)", re.IGNORECASE | re.DOTALL
)
_UNLOAD_TO = re.compile(r"\bTO\s+'((?:[^']|'')*)'", re.IGNORECASE)


@dataclass(frozen=True)
class _UnloadOptions:
    """Redshift ``UNLOAD`` options that control *where/how many* objects are
    written, as opposed to ``_Format`` which controls the bytes inside them.

    ``parallel`` mirrors Redshift's default of writing one object per slice
    (``ON``); ``OFF`` forces a single object named exactly as the target, with
    no slice suffix. ``allow_overwrite`` mirrors Redshift's default of erroring
    when the target already has objects, unless ``ALLOWOVERWRITE`` is given.
    """

    parallel: bool
    allow_overwrite: bool


def parse_unload(sql: str) -> tuple[str, str, _Format, _UnloadOptions]:
    """Pull the inner query, S3 target, format, and options out of an UNLOAD statement.

    sqlglot does not model UNLOAD (it falls back to a generic ``Command``), so we
    parse the text directly.
    """
    qm = _UNLOAD_QUERY.search(sql)
    tm = _UNLOAD_TO.search(sql)
    if not qm or not tm:
        raise ValueError(f"could not parse UNLOAD statement: {sql!r}")
    query = qm.group(1).replace("''", "'")
    target = tm.group(1).replace("''", "'")
    # Everything after the TO clause is where the format/options live; scanning
    # only the tail keeps keywords inside the query or the S3 path from matching.
    options = sql[tm.end() :]
    return query, target, _format_from_options(options), _unload_options_from(options)


def _unload_options_from(options: str) -> _UnloadOptions:
    up = options.upper()
    parallel_m = re.search(r"\bPARALLEL\s+(ON|OFF|TRUE|FALSE)\b", up)
    parallel = parallel_m.group(1) not in ("OFF", "FALSE") if parallel_m else True
    allow_overwrite = bool(re.search(r"\bALLOWOVERWRITE\b", up))
    return _UnloadOptions(parallel=parallel, allow_overwrite=allow_overwrite)


def _format_from_options(options: str) -> _Format:
    delim_m = re.search(r"\bDELIMITER\s+(?:AS\s+)?'((?:[^']|'')*)'", options, re.I)
    fmt_m = re.search(r"\bFORMAT\s+(?:AS\s+)?(CSV|PARQUET|JSON)\b", options, re.I)
    up = options.upper()
    if fmt_m:
        kind = fmt_m.group(1).upper()
    elif re.search(r"\bPARQUET\b", up):
        kind = "PARQUET"
    elif re.search(r"\bCSV\b", up):
        kind = "CSV"
    elif re.search(r"\bJSON\b", up):
        kind = "JSON"
    else:
        kind = "TEXT"
    delimiter = (
        delim_m.group(1).replace("''", "'")
        if delim_m
        else ("," if kind == "CSV" else "|")
    )
    header = bool(re.search(r"\bHEADER\b", up))
    return _Format(kind=kind, delimiter=delimiter, header=header)


def run_unload(conn: duckdb.DuckDBPyConnection, unload_sql: str) -> None:
    """Execute an UNLOAD: run the inner query and upload the result to S3."""
    query, target, fmt, opts = parse_unload(unload_sql)
    duck_query = sqlglot.transpile(query, read="redshift", write="duckdb")[0]
    bucket, key = _split_s3_uri(target)
    # PARALLEL ON (the default) names objects <prefix><slice>_part_<n>, one per
    # slice; a single slice is enough for a mock and COPY finds it by prefix
    # regardless. PARALLEL OFF writes exactly one object named as the target,
    # with no suffix.
    out_key = f"{key}000" if opts.parallel else key

    s3 = _s3_client()
    if not opts.allow_overwrite:
        existing = s3.list_objects_v2(Bucket=bucket, Prefix=key).get("Contents", [])
        if existing:
            raise RuntimeError(
                f"UNLOAD destination s3://{bucket}/{key} already exists; "
                "use ALLOWOVERWRITE to replace it"
            )

    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "out"
        conn.execute(
            f"COPY ({duck_query}) TO '{_sql_quote(str(out))}' ({fmt.write_options()})"
        )
        body = out.read_bytes()
    s3.put_object(Bucket=bucket, Key=out_key, Body=body)


# --- COPY -----------------------------------------------------------------


def is_s3_copy(node: exp.Expression) -> bool:
    """True if ``node`` is a Redshift ``COPY table FROM 's3://...'`` load."""
    if not isinstance(node, exp.Copy) or node.args.get("kind") is not True:
        return False
    files = node.args.get("files") or []
    return bool(files) and str(files[0].name).lower().startswith("s3://")


def _copy_target(node: exp.Copy) -> tuple[str, list[str]]:
    target = node.this
    if isinstance(target, exp.Schema):
        table = target.this.sql(dialect="duckdb")
        columns = [c.sql(dialect="duckdb") for c in target.expressions]
        return table, columns
    return target.sql(dialect="duckdb"), []


def _copy_format(node: exp.Copy) -> _Format:
    kind: str | None = None
    delimiter: str | None = None
    ignore_header = 0
    for param in node.args.get("params") or []:
        key = (param.this.name if param.this else "").upper()
        value = param.args.get("expression")
        if key in ("CSV", "PARQUET", "JSON"):
            kind = key
        elif key == "FORMAT" and value is not None:
            kind = value.name.upper()
        elif key == "DELIMITER" and value is not None:
            delimiter = value.name
        elif key == "IGNOREHEADER" and value is not None:
            ignore_header = int(value.name)
    kind = kind or "TEXT"
    if delimiter is None:
        delimiter = "," if kind == "CSV" else "|"
    return _Format(kind=kind, delimiter=delimiter, header=ignore_header > 0)


def run_copy(conn: duckdb.DuckDBPyConnection, node: exp.Copy) -> None:
    """Execute a COPY: download every object under the prefix and insert it."""
    table, columns = _copy_target(node)
    bucket, key = _split_s3_uri(node.args["files"][0].name)
    fmt = _copy_format(node)

    s3 = _s3_client()
    contents = s3.list_objects_v2(Bucket=bucket, Prefix=key).get("Contents", [])
    if not contents:
        return  # Redshift loads zero rows rather than erroring on an empty prefix.

    col_clause = f" ({', '.join(columns)})" if columns else ""
    with tempfile.TemporaryDirectory() as d:
        for i, obj in enumerate(sorted(contents, key=lambda o: o["Key"])):
            body = s3.get_object(Bucket=bucket, Key=obj["Key"])["Body"].read()
            part = Path(d) / f"part_{i}"
            part.write_bytes(body)
            conn.execute(
                f"INSERT INTO {table}{col_clause} SELECT * FROM {fmt.read_expr(part)}"
            )
