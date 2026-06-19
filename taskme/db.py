"""Acesso ao Postgres via conexão direta (psycopg). Não usa o Supabase MCP.

Uso típico:
    with db.transaction() as cur:
        cur.execute("select ...", params)
        row = cur.fetchone()

`transaction()` faz commit no sucesso e rollback em exceção.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

from . import config


def connect() -> psycopg.Connection:
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL não configurada (.env).")
    return psycopg.connect(config.DATABASE_URL, row_factory=dict_row)


@contextmanager
def transaction() -> Iterator[psycopg.Cursor]:
    """Abre conexão+cursor; commit no fim, rollback em erro."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query_all(sql: str, params: dict[str, Any] | tuple | None = None) -> list[dict]:
    with transaction() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def query_one(sql: str, params: dict[str, Any] | tuple | None = None) -> dict | None:
    with transaction() as cur:
        cur.execute(sql, params)
        return cur.fetchone()
