import hashlib
import json
from pathlib import Path

from flask import current_app

from ..db import get_db
from .backtest_rules import BacktestConflictError, BacktestNotFoundError
from .dataset_store import read_ohlcv_bars


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _order_book_id(ts_code):
    code, _, exchange = ts_code.upper().partition(".")
    suffix = {"SZ": "XSHE", "SH": "XSHG", "BJ": "XBSE"}.get(exchange, exchange)
    return f"{code}.{suffix}" if suffix else code


def _safe_run_dir(run_id):
    root = Path(current_app.config["BACKTEST_DATA_DIR"]).resolve()
    target = (root / "runs" / str(int(run_id))).resolve()
    target.relative_to(root)
    return root, target


def _adjust_rows(rows, asset_type, mode):
    if mode == "raw":
        return rows, "使用原始价格，未模拟分红和除权除息。"

    factors = [row.get("adj_factor") for row in rows if row.get("adj_factor") not in (None, 0)]
    if not factors:
        if asset_type == "stock":
            raise BacktestConflictError("adjustment_factor_required")
        return rows, "该标的缺少复权因子，本次按原始价格运行。"

    anchor = float(factors[-1])
    adjusted = []
    for row in rows:
        factor = row.get("adj_factor")
        if factor in (None, 0):
            raise BacktestConflictError("incomplete_adjustment_factor")
        ratio = float(factor) / anchor
        item = dict(row)
        for field in ("open", "high", "low", "close"):
            if item.get(field) is not None:
                item[field] = round(float(item[field]) * ratio, 6)
        adjusted.append(item)
    return adjusted, "使用所选区间末日作为锚点的前复权价格，不含现金分红入账。"


def build_run_snapshot(run_id):
    db = get_db()
    row = db.execute(
        """
        SELECT br.*, s.name AS strategy_name, sv.code, sv.code_hash,
               i.ts_code, i.name AS instrument_name, i.asset_type
        FROM backtest_runs br
        JOIN strategies s ON s.id = br.strategy_id
        JOIN strategy_versions sv ON sv.id = br.strategy_version_id
        JOIN instruments i ON i.id = br.instrument_id
        WHERE br.id = ?
        """,
        (run_id,),
    ).fetchone()
    if not row:
        raise BacktestNotFoundError("backtest_not_found")
    run = dict(row)

    bars = [
        bar
        for bar in read_ohlcv_bars(run, "daily")
        if run["start_date"] <= bar["trade_date"] <= run["end_date"]
    ]
    if len(bars) < 2:
        raise BacktestConflictError("backtest_data_insufficient")
    if any(bar.get(field) is None for bar in bars for field in ("open", "high", "low", "close")):
        raise BacktestConflictError("backtest_data_incomplete")

    bars, adjustment_warning = _adjust_rows(bars, run["asset_type"], run["adjustment_mode"])
    snapshot = {
        "schema_version": 1,
        "run_id": run_id,
        "instrument": {
            "id": run["instrument_id"],
            "ts_code": run["ts_code"],
            "order_book_id": _order_book_id(run["ts_code"]),
            "name": run["instrument_name"],
            "asset_type": run["asset_type"],
        },
        "frequency": "1d",
        "adjustment_mode": run["adjustment_mode"],
        "start_date": bars[0]["trade_date"],
        "end_date": bars[-1]["trade_date"],
        "bars": bars,
    }
    snapshot_text = _canonical_json(snapshot)
    dataset_hash = hashlib.sha256(snapshot_text.encode("utf-8")).hexdigest()

    root, run_dir = _safe_run_dir(run_id)
    input_dir = run_dir / "input"
    output_dir = run_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir.chmod(0o777)
    snapshot_path = input_dir / "snapshot.json"
    strategy_path = input_dir / "strategy.py"
    config_path = input_dir / "run.json"
    snapshot_path.write_text(snapshot_text, encoding="utf-8")
    strategy_path.write_text(run["code"], encoding="utf-8")
    config_path.write_text(
        _canonical_json(
            {
                "run_id": run_id,
                "start_date": run["start_date"],
                "end_date": run["end_date"],
                "initial_cash": run["initial_cash"],
                "benchmark": run["benchmark"],
                "commission_rate": run["commission_rate"],
                "slippage_rate": run["slippage_rate"],
                "parameters": json.loads(run["parameters_json"] or "{}"),
                "strategy_code_hash": run["code_hash"],
                "dataset_hash": dataset_hash,
            }
        ),
        encoding="utf-8",
    )

    relative_snapshot = snapshot_path.relative_to(root).as_posix()
    db.execute(
        """
        UPDATE backtest_runs
        SET dataset_hash=?, dataset_snapshot_path=?, result_warning=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
        """,
        (dataset_hash, relative_snapshot, adjustment_warning, run_id),
    )
    db.commit()
    return {
        "run": run,
        "run_dir": run_dir,
        "input_dir": input_dir,
        "output_dir": output_dir,
        "snapshot": snapshot,
        "dataset_hash": dataset_hash,
        "warning": adjustment_warning,
    }
