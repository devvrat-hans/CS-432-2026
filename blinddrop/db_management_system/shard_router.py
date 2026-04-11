"""High-level query routing helpers for the sharded Blind Drop system.

Functions here abstract away shard selection so that callers in routes.py
can perform lookups, inserts, and scatter-gather queries without knowing
which shard holds a given record.
"""
import sqlite3
from shard_manager import (
    NUM_SHARDS,
    SHARDED_TABLES,
    ShardManager,
    get_shard_id,
)


def route_lookup(sm, table_name, session_id):
    """Return the shard connection that holds records for *session_id*.

    Parameters
    ----------
    sm : ShardManager
    table_name : str  (used only for validation / future routing changes)
    session_id : int | str

    Returns
    -------
    sqlite3.Connection
    """
    shard_id = get_shard_id(session_id)
    return sm.get_shard_conn(shard_id)


def scatter_gather_query(sm, query, params=None):
    """Run *query* on every shard and return merged rows.

    Parameters
    ----------
    sm : ShardManager
    query : str — SQL SELECT query
    params : tuple | None

    Returns
    -------
    list[sqlite3.Row]  — combined results from all reachable shards
    """
    params = params or ()
    results = []
    for shard_id in range(NUM_SHARDS):
        try:
            conn = sm.get_shard_conn(shard_id)
            rows = conn.execute(query, params).fetchall()
            results.extend(rows)
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            # Shard unavailable — continue with remaining shards.
            pass
    return results


def scatter_gather_count(sm, table_name):
    """Return the total row count for *table_name* across all shards.

    Also returns a per-shard breakdown dict.
    """
    per_shard = {}
    total = 0
    for shard_id in range(NUM_SHARDS):
        try:
            conn = sm.get_shard_conn(shard_id)
            count = conn.execute(
                f"SELECT COUNT(*) AS c FROM {table_name}"
            ).fetchone()["c"]
            per_shard[shard_id] = count
            total += count
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            per_shard[shard_id] = None
    return total, per_shard


def insert_to_shard(sm, table_name, columns, values, session_id):
    """Insert a record into the correct shard determined by *session_id*.

    Parameters
    ----------
    sm : ShardManager
    table_name : str
    columns : list[str]
    values : tuple
    session_id : int | str

    Returns
    -------
    sqlite3.Connection — the shard connection used (caller may still need to commit)
    """
    conn = route_lookup(sm, table_name, session_id)
    col_list = ", ".join(columns)
    placeholders = ", ".join(["?"] * len(columns))
    conn.execute(
        f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})",
        values,
    )
    return conn


def find_token_shard(sm, token_value):
    """Search all shards for a OneTimeToken by *token_value*.

    Returns
    -------
    (sqlite3.Connection, sqlite3.Row) | (None, None)
        The shard connection that holds the token and the token row,
        or (None, None) if the token is not found on any shard.
    """
    for shard_id in range(NUM_SHARDS):
        try:
            conn = sm.get_shard_conn(shard_id)
            row = conn.execute(
                """
                SELECT tokenID, sessionID, tokenValue, createdAt, expiryAt, status
                FROM OneTimeToken
                WHERE tokenValue = ?
                """,
                (token_value,),
            ).fetchone()
            if row is not None:
                return conn, row
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            pass
    return None, None


def find_record_across_shards(sm, table_name, pk_column, pk_value):
    """Search all shards for a record by its primary key.

    Returns
    -------
    (sqlite3.Connection, sqlite3.Row) | (None, None)
    """
    for shard_id in range(NUM_SHARDS):
        try:
            conn = sm.get_shard_conn(shard_id)
            row = conn.execute(
                f"SELECT * FROM {table_name} WHERE {pk_column} = ?",
                (pk_value,),
            ).fetchone()
            if row is not None:
                return conn, row
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            pass
    return None, None


def is_sharded_table(table_name):
    """Return True if *table_name* is one of the sharded domain tables."""
    return table_name in SHARDED_TABLES
