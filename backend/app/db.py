import sqlite3
from pathlib import Path

from flask import current_app, g


def get_db():
    if "db" not in g:
        db_path = Path(current_app.config["DATABASE_PATH"])
        db_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db_path = Path(current_app.config["DATABASE_PATH"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path)
    try:
        db.executescript(SCHEMA)
        _migrate_asset_type_constraints(db)
        db.commit()
    finally:
        db.close()


def _migrate_asset_type_constraints(db):
    table_sql = {
        row[0]: row[1] or ""
        for row in db.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name IN ('instruments', 'research_requests')"
        )
    }
    if all("'index'" in table_sql.get(name, "") for name in ("instruments", "research_requests")):
        return

    db.executescript(
        """
        PRAGMA foreign_keys = OFF;
        BEGIN;

        DROP TABLE IF EXISTS instruments_asset_type_v2;
        CREATE TABLE instruments_asset_type_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            asset_type TEXT NOT NULL CHECK (asset_type IN ('stock', 'etf', 'index', 'fund')),
            market TEXT,
            industry TEXT,
            area TEXT,
            list_date TEXT,
            data_start TEXT,
            data_end TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            is_published INTEGER NOT NULL DEFAULT 0,
            last_synced_at TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO instruments_asset_type_v2
        SELECT id, ts_code, name, asset_type, market, industry, area, list_date,
               data_start, data_end, status, is_published, last_synced_at, notes,
               created_at, updated_at
        FROM instruments;

        DROP TABLE IF EXISTS research_requests_asset_type_v2;
        CREATE TABLE research_requests_asset_type_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            ts_code TEXT NOT NULL,
            asset_type TEXT NOT NULL CHECK (asset_type IN ('stock', 'etf', 'index', 'fund')),
            reason TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO research_requests_asset_type_v2
        SELECT id, user_id, ts_code, asset_type, reason, status, created_at
        FROM research_requests;

        DROP TABLE research_requests;
        DROP TABLE instruments;
        ALTER TABLE instruments_asset_type_v2 RENAME TO instruments;
        ALTER TABLE research_requests_asset_type_v2 RENAME TO research_requests;

        COMMIT;
        PRAGMA foreign_keys = ON;
        """
    )
    violations = db.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(f"Foreign key check failed after asset type migration: {violations}")


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS instruments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL CHECK (asset_type IN ('stock', 'etf', 'index', 'fund')),
    market TEXT,
    industry TEXT,
    area TEXT,
    list_date TEXT,
    data_start TEXT,
    data_end TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    is_published INTEGER NOT NULL DEFAULT 0,
    last_synced_at TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_bars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    freq TEXT NOT NULL CHECK (freq IN ('daily', 'weekly')),
    trade_date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    amount REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(instrument_id, freq, trade_date)
);

CREATE TABLE IF NOT EXISTS sync_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id INTEGER REFERENCES instruments(id) ON DELETE SET NULL,
    status TEXT NOT NULL,
    message TEXT,
    rows_synced INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS research_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    ts_code TEXT NOT NULL,
    asset_type TEXT NOT NULL CHECK (asset_type IN ('stock', 'etf', 'index', 'fund')),
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_price_bars_lookup
ON price_bars(instrument_id, freq, trade_date);

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
