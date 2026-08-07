import json
import math
import os
import sys
from pathlib import Path

import pandas as pd
import rqalpha


INPUT_DIR = Path("/input")
OUTPUT_DIR = Path("/output")


def clean(value):
    if isinstance(value, dict):
        return {str(key): clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        return clean(value.item())
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def frame_records(frame):
    if frame is None or not hasattr(frame, "reset_index"):
        return []
    records = frame.reset_index().to_dict(orient="records")
    return clean(records)


def equity_records(portfolio):
    if portfolio is None or portfolio.empty:
        return []
    frame = portfolio.reset_index()
    date_column = "date" if "date" in frame.columns else frame.columns[0]
    output = []
    for row in frame.to_dict(orient="records"):
        output.append(
            clean(
                {
                    "date": row.get(date_column),
                    "unit_net_value": row.get("unit_net_value"),
                    "total_value": row.get("total_value"),
                    "benchmark_unit_net_value": row.get("benchmark_unit_net_value"),
                }
            )
        )
    return output


def drawdown_records(equity):
    peak = None
    output = []
    for row in equity:
        value = row.get("unit_net_value")
        if value is None:
            continue
        peak = value if peak is None else max(peak, value)
        output.append({"date": row["date"], "drawdown": value / peak - 1 if peak else 0})
    return output


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_config = json.loads((INPUT_DIR / "run.json").read_text(encoding="utf-8"))
    snapshot = json.loads((INPUT_DIR / "snapshot.json").read_text(encoding="utf-8"))
    strategy_code = (INPUT_DIR / "strategy.py").read_text(encoding="utf-8")
    commission_multiplier = float(run_config["commission_rate"]) / 0.0008
    config = {
        "base": {
            "start_date": run_config["start_date"],
            "end_date": run_config["end_date"],
            "frequency": "1d",
            "data_bundle_path": "/bundle",
            "benchmark": run_config.get("benchmark"),
            "accounts": {"stock": float(run_config["initial_cash"])},
        },
        "extra": {
            "log_level": "error",
            "context_vars": run_config.get("parameters") or {},
        },
        "mod": {
            "quant_lab": {
                "enabled": True,
                "lib": "rqalpha_mod_quant_lab",
                "snapshot_path": "/input/snapshot.json",
            },
            "sys_simulation": {
                "enabled": True,
                "matching_type": "current_bar",
                "slippage_model": "PriceRatioSlippage",
                "slippage": float(run_config["slippage_rate"]),
            },
            "sys_transaction_cost": {
                "enabled": True,
                "cn_stock_min_commission": 0,
                "stock_commission_multiplier": commission_multiplier,
            },
            "sys_analyser": {"enabled": True},
        },
    }
    result = rqalpha.run_code(strategy_code, config=config)
    summary = result.get("summary") or {}
    trades = frame_records(result.get("trades"))
    equity = equity_records(result.get("portfolio"))
    normalized_summary = {
        "total_return": summary.get("total_returns"),
        "annual_return": summary.get("annualized_returns"),
        "max_drawdown": summary.get("max_drawdown"),
        "sharpe": summary.get("sharpe"),
        "volatility": summary.get("volatility"),
        "win_rate": summary.get("win_rate"),
        "trade_count": len(trades),
    }
    output = clean(
        {
            "engine_name": "rqalpha",
            "engine_version": rqalpha.__version__,
            "exit_code": 0,
            "warning": "前复权行情不含现金分红入账；结果用于研究学习，不代表实盘表现。",
            "summary": normalized_summary,
            "equity_curve": equity,
            "drawdown_curve": drawdown_records(equity),
            "trades": trades,
            "positions": frame_records(result.get("positions")),
            "raw_output": {
                "rqalpha_summary": summary,
                "instrument": snapshot["instrument"],
            },
        }
    )
    (OUTPUT_DIR / "result.json").write_text(
        json.dumps(output, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"RQAlpha runner failed: {exc}", file=sys.stderr)
        raise
