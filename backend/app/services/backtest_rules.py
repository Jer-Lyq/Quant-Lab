import json
from datetime import datetime


MAX_PARAMETERS_BYTES = 32 * 1024
SUPPORTED_ASSET_TYPES = {"stock", "etf"}
SUPPORTED_FREQUENCIES = {"daily"}
SUPPORTED_ADJUSTMENTS = {"qfq", "raw"}


class BacktestError(Exception):
    status_code = 400

    def __init__(self, code):
        super().__init__(code)
        self.code = code


class BacktestNotFoundError(BacktestError):
    status_code = 404


class BacktestPermissionError(BacktestError):
    status_code = 403


class BacktestConflictError(BacktestError):
    status_code = 409


def _positive_int(payload, field):
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise BacktestError(f"invalid_{field}")
    return value


def _date(payload, field):
    value = payload.get(field)
    if not isinstance(value, str):
        raise BacktestError(f"invalid_{field}")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise BacktestError(f"invalid_{field}") from exc


def _rate(payload, field, default):
    value = payload.get(field, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BacktestError(f"invalid_{field}")
    value = float(value)
    if value < 0 or value > 0.02:
        raise BacktestError(f"invalid_{field}")
    return value


def normalize_backtest_payload(payload):
    if not isinstance(payload, dict):
        raise BacktestError("json_object_required")

    start_date = _date(payload, "start_date")
    end_date = _date(payload, "end_date")
    if end_date <= start_date:
        raise BacktestError("invalid_backtest_date_range")

    initial_cash = payload.get("initial_cash", 1_000_000)
    if isinstance(initial_cash, bool) or not isinstance(initial_cash, (int, float)):
        raise BacktestError("invalid_initial_cash")
    initial_cash = float(initial_cash)
    if initial_cash < 10_000 or initial_cash > 10_000_000_000:
        raise BacktestError("invalid_initial_cash")

    freq = payload.get("freq", "daily")
    if freq not in SUPPORTED_FREQUENCIES:
        raise BacktestError("unsupported_backtest_frequency")

    adjustment_mode = payload.get("adjustment_mode", "qfq")
    if adjustment_mode not in SUPPORTED_ADJUSTMENTS:
        raise BacktestError("invalid_adjustment_mode")

    parameters = payload.get("parameters", {})
    if not isinstance(parameters, dict):
        raise BacktestError("invalid_parameters")
    encoded_parameters = json.dumps(parameters, ensure_ascii=False, sort_keys=True)
    if len(encoded_parameters.encode("utf-8")) > MAX_PARAMETERS_BYTES:
        raise BacktestError("parameters_too_large")

    benchmark = payload.get("benchmark")
    if benchmark is not None:
        if not isinstance(benchmark, str) or len(benchmark.strip()) > 40:
            raise BacktestError("invalid_benchmark")
        benchmark = benchmark.strip() or None

    return {
        "strategy_id": _positive_int(payload, "strategy_id"),
        "strategy_version_id": _positive_int(payload, "strategy_version_id"),
        "instrument_id": _positive_int(payload, "instrument_id"),
        "freq": freq,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "initial_cash": initial_cash,
        "benchmark": benchmark,
        "commission_rate": _rate(payload, "commission_rate", 0.0003),
        "slippage_rate": _rate(payload, "slippage_rate", 0.0001),
        "adjustment_mode": adjustment_mode,
        "parameters": parameters,
    }
