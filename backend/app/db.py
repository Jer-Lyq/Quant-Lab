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
        _migrate_strategy_idea(db)
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


def _migrate_strategy_idea(db):
    columns = {
        row[1]
        for row in db.execute("PRAGMA table_info(strategies)").fetchall()
    }
    if "strategy_idea" not in columns:
        db.execute("ALTER TABLE strategies ADD COLUMN strategy_idea TEXT")


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

CREATE TABLE IF NOT EXISTS strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    strategy_idea TEXT,
    uploader_notes TEXT,
    strategy_type TEXT NOT NULL DEFAULT 'custom'
        CHECK (strategy_type IN ('trend', 'mean_reversion', 'breakout', 'momentum', 'timing', 'custom')),
    market TEXT,
    freq TEXT NOT NULL DEFAULT 'daily' CHECK (freq IN ('daily', 'weekly')),
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'ready', 'backtesting', 'validated', 'discarded')),
    author_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS strategy_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    version_name TEXT NOT NULL,
    code TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    notes TEXT,
    validation_status TEXT NOT NULL DEFAULT 'unchecked'
        CHECK (validation_status IN ('unchecked', 'valid', 'invalid')),
    validation_message TEXT,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS strategy_instruments (
    strategy_id INTEGER NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (strategy_id, instrument_id)
);

CREATE TABLE IF NOT EXISTS backtest_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    strategy_version_id INTEGER NOT NULL REFERENCES strategy_versions(id) ON DELETE RESTRICT,
    instrument_id INTEGER REFERENCES instruments(id) ON DELETE SET NULL,
    universe_config_json TEXT,
    freq TEXT NOT NULL DEFAULT 'daily' CHECK (freq IN ('daily', 'weekly')),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    initial_cash REAL NOT NULL DEFAULT 1000000,
    benchmark TEXT,
    commission_rate REAL NOT NULL DEFAULT 0,
    slippage_rate REAL NOT NULL DEFAULT 0,
    parameters_json TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'queued', 'running', 'success', 'failed', 'cancelled')),
    error_message TEXT,
    total_return REAL,
    annual_return REAL,
    max_drawdown REAL,
    sharpe REAL,
    volatility REAL,
    win_rate REAL,
    trade_count INTEGER,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    queued_at TEXT,
    started_at TEXT,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS backtest_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'success', 'failed', 'cancelled')),
    priority INTEGER NOT NULL DEFAULT 100,
    attempts INTEGER NOT NULL DEFAULT 0,
    locked_by TEXT,
    locked_until TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS backtest_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL
        CHECK (artifact_type IN ('summary', 'equity_curve', 'drawdown_curve', 'trades', 'positions', 'raw_output')),
    storage_kind TEXT NOT NULL DEFAULT 'json'
        CHECK (storage_kind IN ('json', 'file')),
    json_data TEXT,
    relative_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_strategy_versions_strategy
ON strategy_versions(strategy_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy
ON backtest_runs(strategy_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_backtest_jobs_status
ON backtest_jobs(status, priority, created_at);
"""
