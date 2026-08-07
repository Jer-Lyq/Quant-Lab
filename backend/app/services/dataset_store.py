import re
import shutil
import sqlite3
from pathlib import Path

from flask import current_app

from ..db import get_db


OHLCV_SCHEMA = """
CREATE TABLE IF NOT EXISTS ohlcv_bars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    freq TEXT NOT NULL CHECK (freq IN ('daily', 'weekly')),
    trade_date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    amount REAL,
    adj_factor REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(freq, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_ohlcv_bars_lookup
ON ohlcv_bars(freq, trade_date);
"""


CATALOG_DATASET_SCHEMA = """
CREATE TABLE IF NOT EXISTS instrument_datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    dataset_type TEXT NOT NULL,
    storage_kind TEXT NOT NULL DEFAULT 'sqlite',
    relative_path TEXT NOT NULL,
    row_count INTEGER NOT NULL DEFAULT 0,
    min_date TEXT,
    max_date TEXT,
    source TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(instrument_id, dataset_type)
);
"""


def instrument_data_root():
    return Path(current_app.config["INSTRUMENT_DATA_DIR"])


def instrument_dir(instrument):
    asset_type = _safe_segment(instrument["asset_type"] or "unknown").lower()
    ts_code = _safe_segment(instrument["ts_code"]).upper()
    return instrument_data_root() / asset_type / ts_code


def ohlcv_path(instrument):
    return instrument_dir(instrument) / "ohlcv.sqlite3"


def delete_instrument_data(instrument):
    root = instrument_data_root().resolve()
    target = instrument_dir(instrument).resolve()
    if target == root:
        raise RuntimeError("Refusing to delete instrument data root.")
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("Refusing to delete data outside instrument data root.") from exc
    if target.exists():
        shutil.rmtree(target)


def read_ohlcv_bars(instrument, freq):
    if freq not in {"daily", "weekly"}:
        return []
    ensure_ohlcv_from_legacy(instrument)
    path = ohlcv_path(instrument)
    if not path.exists():
        return []
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_ohlcv_schema(conn)
        rows = conn.execute(
            """
            SELECT trade_date, open, high, low, close, volume, amount, adj_factor
            FROM ohlcv_bars
            WHERE freq=?
            ORDER BY trade_date ASC
            """,
            (freq,),
        ).fetchall()
    return [dict(row) for row in rows]


def replace_ohlcv_bars(instrument, rows_by_freq, source="tushare"):
    path = ohlcv_path(instrument)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        _ensure_ohlcv_schema(conn)
        conn.execute("BEGIN")
        conn.execute("DELETE FROM ohlcv_bars")
        total_rows = 0
        min_date = None
        max_date = None
        for freq, rows in rows_by_freq.items():
            for row in rows:
                trade_date = row["trade_date"]
                conn.execute(
                    """
                    INSERT INTO ohlcv_bars
                    (freq, trade_date, open, high, low, close, volume, amount, adj_factor)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        freq,
                        trade_date,
                        row["open"],
                        row["high"],
                        row["low"],
                        row["close"],
                        row["volume"],
                        row["amount"],
                        row.get("adj_factor"),
                    ),
                )
                total_rows += 1
                min_date = trade_date if min_date is None else min(min_date, trade_date)
                max_date = trade_date if max_date is None else max(max_date, trade_date)
        conn.commit()

    _upsert_catalog_dataset(instrument, path, total_rows, min_date, max_date, source)
    return {"row_count": total_rows, "min_date": min_date, "max_date": max_date, "path": str(path)}


def ensure_ohlcv_from_legacy(instrument):
    path = ohlcv_path(instrument)
    if path.exists():
        return
    db = get_db()
    _ensure_catalog_dataset_table(db)
    try:
        legacy_rows = db.execute(
            """
            SELECT freq, trade_date, open, high, low, close, volume, amount
            FROM price_bars
            WHERE instrument_id=?
            ORDER BY freq, trade_date
            """,
            (instrument["id"],),
        ).fetchall()
    except sqlite3.OperationalError:
        legacy_rows = []
    if not legacy_rows:
        return
    rows_by_freq = {"daily": [], "weekly": []}
    for row in legacy_rows:
        rows_by_freq[row["freq"]].append(
            {
                "trade_date": row["trade_date"],
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
                "amount": row["amount"],
                "adj_factor": row["adj_factor"] if "adj_factor" in row.keys() else None,
            }
        )
    replace_ohlcv_bars(instrument, rows_by_freq, source="legacy-price_bars")


def _upsert_catalog_dataset(instrument, path, row_count, min_date, max_date, source):
    db = get_db()
    _ensure_catalog_dataset_table(db)
    relative_path = _relative_path(path)
    db.execute(
        """
        INSERT INTO instrument_datasets
        (instrument_id, dataset_type, storage_kind, relative_path, row_count, min_date, max_date, source, updated_at)
        VALUES (?, 'ohlcv', 'sqlite', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(instrument_id, dataset_type) DO UPDATE SET
            storage_kind=excluded.storage_kind,
            relative_path=excluded.relative_path,
            row_count=excluded.row_count,
            min_date=excluded.min_date,
            max_date=excluded.max_date,
            source=excluded.source,
            updated_at=CURRENT_TIMESTAMP
        """,
        (instrument["id"], relative_path, row_count, min_date, max_date, source),
    )
    db.commit()


def _ensure_catalog_dataset_table(db):
    db.executescript(CATALOG_DATASET_SCHEMA)


def _ensure_ohlcv_schema(conn):
    conn.executescript(OHLCV_SCHEMA)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(ohlcv_bars)").fetchall()}
    if "adj_factor" not in columns:
        conn.execute("ALTER TABLE ohlcv_bars ADD COLUMN adj_factor REAL")
        conn.commit()


def _relative_path(path):
    try:
        return str(path.relative_to(instrument_data_root())).replace("\\", "/")
    except ValueError:
        return str(path)


def _safe_segment(value):
    return re.sub(r"[^0-9A-Za-z._-]+", "_", str(value).strip())
