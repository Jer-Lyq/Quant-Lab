import hashlib
import json
from pathlib import Path

from flask import current_app

from ..db import get_db
from .backtest_rules import (
    SUPPORTED_ASSET_TYPES,
    BacktestConflictError,
    BacktestNotFoundError,
    BacktestPermissionError,
    normalize_backtest_payload,
)
from .dataset_store import read_ohlcv_bars


ACTIVE_STATUSES = {"pending", "queued", "running"}
TERMINAL_STATUSES = {"success", "failed", "cancelled"}


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_json(value):
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _run_row(run_id):
    row = get_db().execute(
        """
        SELECT br.*, s.name AS strategy_name, sv.version_name,
               i.ts_code, i.name AS instrument_name, i.asset_type,
               u.username AS created_by_name
        FROM backtest_runs br
        JOIN strategies s ON s.id = br.strategy_id
        JOIN strategy_versions sv ON sv.id = br.strategy_version_id
        LEFT JOIN instruments i ON i.id = br.instrument_id
        LEFT JOIN users u ON u.id = br.created_by
        WHERE br.id = ?
        """,
        (run_id,),
    ).fetchone()
    return dict(row) if row else None


def get_backtest(run_id):
    run = _run_row(run_id)
    if not run:
        raise BacktestNotFoundError("backtest_not_found")
    return run


def list_backtests(strategy_id=None, status=None, limit=100):
    limit = max(1, min(int(limit), 200))
    conditions = []
    params = []
    if strategy_id is not None:
        conditions.append("br.strategy_id = ?")
        params.append(int(strategy_id))
    if status:
        conditions.append("br.status = ?")
        params.append(status)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = get_db().execute(
        f"""
        SELECT br.*, s.name AS strategy_name, sv.version_name,
               i.ts_code, i.name AS instrument_name, u.username AS created_by_name
        FROM backtest_runs br
        JOIN strategies s ON s.id = br.strategy_id
        JOIN strategy_versions sv ON sv.id = br.strategy_version_id
        LEFT JOIN instruments i ON i.id = br.instrument_id
        LEFT JOIN users u ON u.id = br.created_by
        {where}
        ORDER BY br.created_at DESC, br.id DESC
        LIMIT ?
        """,
        (*params, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def backtest_options(strategy_id):
    db = get_db()
    strategy = db.execute("SELECT * FROM strategies WHERE id=?", (strategy_id,)).fetchone()
    if not strategy:
        raise BacktestNotFoundError("strategy_not_found")
    versions = db.execute(
        """
        SELECT id, strategy_id, version_name, code_hash, validation_status,
               validation_message, created_at
        FROM strategy_versions
        WHERE strategy_id=?
        ORDER BY created_at DESC, id DESC
        """,
        (strategy_id,),
    ).fetchall()
    instruments = db.execute(
        """
        SELECT i.*
        FROM strategy_instruments si
        JOIN instruments i ON i.id=si.instrument_id
        WHERE si.strategy_id=?
        ORDER BY i.name, i.ts_code
        """,
        (strategy_id,),
    ).fetchall()
    instrument_options = []
    for row in instruments:
        instrument = dict(row)
        bars = read_ohlcv_bars(instrument, "daily")
        instrument["backtest_supported"] = instrument["asset_type"] in SUPPORTED_ASSET_TYPES
        instrument["bar_count"] = len(bars)
        instrument["data_start"] = bars[0]["trade_date"] if bars else None
        instrument["data_end"] = bars[-1]["trade_date"] if bars else None
        instrument["has_adjustment_factor"] = any(bar.get("adj_factor") not in (None, 0) for bar in bars)
        instrument_options.append(instrument)
    return {
        "strategy": dict(strategy),
        "versions": [dict(row) for row in versions],
        "instruments": instrument_options,
        "defaults": {
            "freq": "daily",
            "initial_cash": 1_000_000,
            "commission_rate": 0.0003,
            "slippage_rate": 0.0001,
            "adjustment_mode": "qfq",
        },
    }


def create_backtest(payload, user):
    data = normalize_backtest_payload(payload)
    db = get_db()
    strategy = db.execute("SELECT * FROM strategies WHERE id=?", (data["strategy_id"],)).fetchone()
    if not strategy:
        raise BacktestNotFoundError("strategy_not_found")
    if strategy["status"] == "discarded":
        raise BacktestConflictError("discarded_strategy_read_only")

    version = db.execute("SELECT * FROM strategy_versions WHERE id=?", (data["strategy_version_id"],)).fetchone()
    if not version or version["strategy_id"] != data["strategy_id"]:
        raise BacktestNotFoundError("strategy_version_not_found")
    if version["validation_status"] != "valid":
        raise BacktestConflictError("strategy_version_invalid")

    instrument = db.execute(
        """
        SELECT i.*
        FROM instruments i
        JOIN strategy_instruments si ON si.instrument_id=i.id
        WHERE i.id=? AND si.strategy_id=?
        """,
        (data["instrument_id"], data["strategy_id"]),
    ).fetchone()
    if not instrument:
        raise BacktestConflictError("strategy_instrument_required")
    if instrument["asset_type"] not in SUPPORTED_ASSET_TYPES:
        raise BacktestConflictError("unsupported_backtest_asset_type")

    bars = [
        row
        for row in read_ohlcv_bars(dict(instrument), "daily")
        if data["start_date"] <= row["trade_date"] <= data["end_date"]
    ]
    if len(bars) < 2:
        raise BacktestConflictError("backtest_data_insufficient")

    config = {
        "strategy_id": data["strategy_id"],
        "strategy_version_id": data["strategy_version_id"],
        "instrument_id": data["instrument_id"],
        "freq": data["freq"],
        "start_date": data["start_date"],
        "end_date": data["end_date"],
        "initial_cash": data["initial_cash"],
        "benchmark": data["benchmark"],
        "commission_rate": data["commission_rate"],
        "slippage_rate": data["slippage_rate"],
        "adjustment_mode": data["adjustment_mode"],
        "parameters": data["parameters"],
    }
    with db:
        cursor = db.execute(
            """
            INSERT INTO backtest_runs
            (strategy_id, strategy_version_id, instrument_id, freq, start_date, end_date,
             initial_cash, benchmark, commission_rate, slippage_rate, parameters_json,
             engine_name, strategy_code_hash, normalized_config_json, config_hash,
             adjustment_mode, status, created_by, queued_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'rqalpha', ?, ?, ?, ?, 'queued', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                data["strategy_id"], data["strategy_version_id"], data["instrument_id"], data["freq"],
                data["start_date"], data["end_date"], data["initial_cash"], data["benchmark"],
                data["commission_rate"], data["slippage_rate"], _canonical_json(data["parameters"]),
                version["code_hash"], _canonical_json(config), _hash_json(config), data["adjustment_mode"], user["id"],
            ),
        )
        run_id = cursor.lastrowid
        db.execute("INSERT INTO backtest_jobs (run_id, status) VALUES (?, 'pending')", (run_id,))
    return get_backtest(run_id)


def cancel_backtest(run_id, user):
    run = get_backtest(run_id)
    if user["role"] != "admin" and run["created_by"] != user["id"]:
        raise BacktestPermissionError("backtest_cancel_denied")
    if run["status"] in TERMINAL_STATUSES:
        return run

    db = get_db()
    with db:
        if run["status"] in {"pending", "queued"}:
            db.execute(
                "UPDATE backtest_runs SET status='cancelled', cancel_requested_at=CURRENT_TIMESTAMP, finished_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (run_id,),
            )
            db.execute("UPDATE backtest_jobs SET status='cancelled', updated_at=CURRENT_TIMESTAMP WHERE run_id=?", (run_id,))
        else:
            db.execute(
                "UPDATE backtest_runs SET cancel_requested_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (run_id,),
            )
    return get_backtest(run_id)


def _artifact_root():
    return Path(current_app.config["BACKTEST_DATA_DIR"]).resolve()


def save_artifact(run_id, artifact_type, value):
    root = _artifact_root()
    artifact_dir = (root / "runs" / str(int(run_id)) / "artifacts").resolve()
    artifact_dir.relative_to(root)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / f"{artifact_type}.json"
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    relative_path = path.relative_to(root).as_posix()
    db = get_db()
    db.execute("DELETE FROM backtest_artifacts WHERE run_id=? AND artifact_type=?", (run_id, artifact_type))
    db.execute(
        """
        INSERT INTO backtest_artifacts (run_id, artifact_type, storage_kind, relative_path)
        VALUES (?, ?, 'file', ?)
        """,
        (run_id, artifact_type, relative_path),
    )


def get_backtest_artifacts(run_id):
    get_backtest(run_id)
    rows = get_db().execute(
        "SELECT * FROM backtest_artifacts WHERE run_id=? ORDER BY id",
        (run_id,),
    ).fetchall()
    root = _artifact_root()
    output = {}
    for row in rows:
        item = dict(row)
        if item["storage_kind"] == "json":
            output[item["artifact_type"]] = json.loads(item["json_data"] or "null")
            continue
        path = (root / item["relative_path"]).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if path.exists() and path.stat().st_size <= 10 * 1024 * 1024:
            output[item["artifact_type"]] = json.loads(path.read_text(encoding="utf-8"))
    return output


def finish_backtest_success(run_id, result, snapshot):
    summary = result.get("summary") or {}
    db = get_db()
    with db:
        save_artifact(run_id, "summary", summary)
        for artifact_type in ("equity_curve", "drawdown_curve", "trades", "positions", "raw_output"):
            if artifact_type in result:
                save_artifact(run_id, artifact_type, result[artifact_type])
        db.execute(
            """
            UPDATE backtest_runs
            SET status='success', total_return=?, annual_return=?, max_drawdown=?, sharpe=?, volatility=?,
                win_rate=?, trade_count=?, engine_name=?, engine_version=?, worker_version=?, exit_code=?,
                dataset_hash=?, dataset_snapshot_path=?, result_warning=?, finished_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP, error_message=NULL
            WHERE id=?
            """,
            (
                summary.get("total_return"), summary.get("annual_return"), summary.get("max_drawdown"),
                summary.get("sharpe"), summary.get("volatility"), summary.get("win_rate"), summary.get("trade_count"),
                result.get("engine_name", "rqalpha"), result.get("engine_version"), result.get("worker_version"),
                result.get("exit_code", 0), snapshot["dataset_hash"],
                snapshot["run"]["dataset_snapshot_path"] if snapshot["run"].get("dataset_snapshot_path") else f"runs/{run_id}/input/snapshot.json",
                result.get("warning") or snapshot.get("warning"), run_id,
            ),
        )
        db.execute("UPDATE backtest_jobs SET status='success', locked_until=NULL, updated_at=CURRENT_TIMESTAMP WHERE run_id=?", (run_id,))


def finish_backtest_failure(run_id, message, exit_code=None, raw_output=None):
    message = str(message)[:4000]
    db = get_db()
    with db:
        if raw_output:
            save_artifact(run_id, "raw_output", {"log": str(raw_output)[-65536:]})
        db.execute(
            """
            UPDATE backtest_runs
            SET status='failed', error_message=?, exit_code=?, finished_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (message, exit_code, run_id),
        )
        db.execute(
            "UPDATE backtest_jobs SET status='failed', error_message=?, locked_until=NULL, updated_at=CURRENT_TIMESTAMP WHERE run_id=?",
            (message, run_id),
        )
