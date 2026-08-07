import sqlite3

from flask import Blueprint, current_app, g, jsonify, request

from ..auth import require_auth
from ..services.backtest_rules import BacktestError
from ..services.backtest_service import (
    backtest_options,
    cancel_backtest,
    create_backtest,
    get_backtest,
    get_backtest_artifacts,
    list_backtests,
)


backtests_bp = Blueprint("backtests", __name__)


def _error(exc):
    if isinstance(exc, BacktestError):
        return jsonify({"error": exc.code}), exc.status_code
    if isinstance(exc, sqlite3.IntegrityError):
        current_app.logger.warning("Backtest database conflict", exc_info=True)
        return jsonify({"error": "backtest_database_conflict"}), 409
    current_app.logger.exception("Unexpected backtest operation failure")
    return jsonify({"error": "backtest_operation_failed"}), 500


@backtests_bp.get("/backtests/options")
@require_auth
def options():
    try:
        strategy_id = int(request.args.get("strategy_id", ""))
        return jsonify(backtest_options(strategy_id))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_strategy_id"}), 400
    except Exception as exc:
        return _error(exc)


@backtests_bp.get("/backtests")
@require_auth
def backtests():
    try:
        strategy_id = request.args.get("strategy_id")
        return jsonify(
            {
                "backtests": list_backtests(
                    strategy_id=int(strategy_id) if strategy_id else None,
                    status=request.args.get("status"),
                    limit=request.args.get("limit", 100),
                )
            }
        )
    except Exception as exc:
        return _error(exc)


@backtests_bp.post("/backtests")
@require_auth
def create_backtest_route():
    try:
        run = create_backtest(request.get_json(silent=True), g.current_user)
        return jsonify({"backtest": run}), 202
    except Exception as exc:
        return _error(exc)


@backtests_bp.get("/backtests/<int:run_id>")
@require_auth
def backtest_detail(run_id):
    try:
        return jsonify({"backtest": get_backtest(run_id)})
    except Exception as exc:
        return _error(exc)


@backtests_bp.post("/backtests/<int:run_id>/cancel")
@require_auth
def cancel_backtest_route(run_id):
    try:
        return jsonify({"backtest": cancel_backtest(run_id, g.current_user)})
    except Exception as exc:
        return _error(exc)


@backtests_bp.get("/backtests/<int:run_id>/artifacts")
@require_auth
def backtest_artifacts(run_id):
    try:
        return jsonify({"artifacts": get_backtest_artifacts(run_id)})
    except Exception as exc:
        return _error(exc)
