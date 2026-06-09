"""Persistance SQLite des offres agrégées."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from .models import Deal

DB_PATH = Path(__file__).resolve().parent.parent / "deals.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    retailer TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT DEFAULT 'Divers',
    price REAL NOT NULL,
    original_price REAL,
    discount_percent REAL,
    unit TEXT DEFAULT '',
    image_url TEXT DEFAULT '',
    deal_url TEXT DEFAULT '',
    valid_from TEXT,
    valid_until TEXT,
    fetched_at TEXT NOT NULL,
    is_sample INTEGER DEFAULT 0,
    dedupe_key TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_deals_retailer ON deals (retailer);
CREATE INDEX IF NOT EXISTS idx_deals_discount ON deals (discount_percent);

CREATE TABLE IF NOT EXISTS refresh_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ran_at TEXT NOT NULL,
    deals_count INTEGER NOT NULL,
    sources TEXT NOT NULL
);
"""


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def replace_deals(deals: list[Deal], sources: list[str]) -> int:
    """Remplace les offres du jour par le nouveau lot agrégé."""
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute("DELETE FROM deals")
        inserted = 0
        for deal in deals:
            try:
                conn.execute(
                    """INSERT INTO deals
                       (retailer, title, description, category, price,
                        original_price, discount_percent, unit, image_url,
                        deal_url, valid_from, valid_until, fetched_at,
                        is_sample, dedupe_key)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        deal.retailer,
                        deal.title,
                        deal.description,
                        deal.category,
                        deal.price,
                        deal.original_price,
                        deal.discount_percent,
                        deal.unit,
                        deal.image_url,
                        deal.deal_url,
                        deal.valid_from.isoformat() if deal.valid_from else None,
                        deal.valid_until.isoformat() if deal.valid_until else None,
                        now,
                        1 if deal.is_sample else 0,
                        deal.dedupe_key(),
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                continue  # doublon
        conn.execute(
            "INSERT INTO refresh_log (ran_at, deals_count, sources) VALUES (?, ?, ?)",
            (now, inserted, ",".join(sources)),
        )
    return inserted


def query_deals(
    retailer: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_discount: Optional[float] = None,
    sort: str = "discount",
    limit: int = 200,
) -> list[dict]:
    sql = "SELECT * FROM deals WHERE 1=1"
    params: list = []
    if retailer:
        sql += " AND LOWER(retailer) = LOWER(?)"
        params.append(retailer)
    if category:
        sql += " AND LOWER(category) = LOWER(?)"
        params.append(category)
    if search:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if min_discount is not None:
        sql += " AND discount_percent >= ?"
        params.append(min_discount)

    order = {
        "discount": "discount_percent DESC NULLS LAST",
        "price": "price ASC",
        "retailer": "retailer ASC, discount_percent DESC",
    }.get(sort, "discount_percent DESC NULLS LAST")
    sql += f" ORDER BY {order} LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def get_stats() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM deals").fetchone()["c"]
        retailers = [
            dict(r)
            for r in conn.execute(
                "SELECT retailer, COUNT(*) AS count FROM deals GROUP BY retailer"
            ).fetchall()
        ]
        categories = [
            r["category"]
            for r in conn.execute(
                "SELECT DISTINCT category FROM deals ORDER BY category"
            ).fetchall()
        ]
        last = conn.execute(
            "SELECT ran_at, sources FROM refresh_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return {
        "total_deals": total,
        "retailers": retailers,
        "categories": categories,
        "last_refresh": dict(last) if last else None,
    }
