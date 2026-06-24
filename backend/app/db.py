import re
from contextlib import contextmanager

import oracledb

from app.config import settings

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$#]*$")


def _validate_identifier(name: str) -> str:
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid Oracle identifier in config: {name!r}")
    return name


# Validate configured view names once at import time so a bad .env value
# fails fast instead of silently enabling SQL injection via f-string interpolation.
PIC_SUMMARY_VIEW = _validate_identifier(settings.oracle_pic_summary_view)
PIC_DETAIL_VIEW = _validate_identifier(settings.oracle_pic_detail_view)

_pool = oracledb.create_pool(
    user=settings.oracle_user,
    password=settings.oracle_password,
    dsn=settings.oracle_dsn,
    min=1,
    max=8,
    increment=1,
)


@contextmanager
def get_connection():
    conn = _pool.acquire()
    try:
        # Belt-and-suspenders: the DB user should already be read-only,
        # but reject writes for the duration of this transaction too.
        cursor = conn.cursor()
        cursor.execute("SET TRANSACTION READ ONLY")
        cursor.close()
        yield conn
    finally:
        _pool.release(conn)


def fetch_all(sql: str, params: dict | None = None) -> list[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params or {})
        columns = [col[0].lower() for col in cursor.description]
        rows = cursor.fetchall()
        cursor.close()
        return [dict(zip(columns, row)) for row in rows]
