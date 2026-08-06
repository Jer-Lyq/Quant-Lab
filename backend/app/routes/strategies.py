import sqlite3

from flask import Blueprint, g, jsonify, request

from ..auth import require_auth
from ..services.strategy_service import (
    DEFAULT_RQALPHA_CODE,
    add_strategy_instrument,
    create_strategy,
    create_strategy_version,
    delete_strategy,
    delete_strategy_version,
    get_strategy,
    get_strategy_version,
    latest_backtests,
    list_strategies,
    list_strategy_instruments,
    list_strategy_versions,
    remove_strategy_instrument,
    update_strategy,
)

strategies_bp = Blueprint("strategies", __name__)


def _handle_error(exc):
    if isinstance(exc, LookupError):
        return jsonify({"error": str(exc)}), 404
    if isinstance(exc, PermissionError):
        return jsonify({"error": str(exc)}), 403
    if isinstance(exc, ValueError):
        return jsonify({"error": str(exc)}), 400
    if isinstance(exc, sqlite3.IntegrityError):
        return jsonify({"error": "strategy_database_conflict", "message": str(exc)}), 409
    if isinstance(exc, sqlite3.OperationalError):
        return jsonify({"error": "strategy_database_error", "message": str(exc)}), 500
    return jsonify({"error": "strategy_operation_failed", "message": str(exc)}), 500


@strategies_bp.get("/strategies")
@require_auth
def strategies():
    return jsonify({"strategies": list_strategies()})


@strategies_bp.post("/strategies")
@require_auth
def create_strategy_route():
    try:
        strategy = create_strategy(request.get_json(silent=True) or {}, g.current_user)
        return jsonify({"strategy": strategy}), 201
    except Exception as exc:
        return _handle_error(exc)


@strategies_bp.get("/strategies/<int:strategy_id>")
@require_auth
def strategy_detail(strategy_id):
    strategy = get_strategy(strategy_id)
    if not strategy:
        return jsonify({"error": "strategy_not_found"}), 404
    return jsonify(
        {
            "strategy": strategy,
            "versions": list_strategy_versions(strategy_id),
            "instruments": list_strategy_instruments(strategy_id),
            "recent_backtests": latest_backtests(strategy_id),
            "default_code": DEFAULT_RQALPHA_CODE,
        }
    )


@strategies_bp.patch("/strategies/<int:strategy_id>")
@require_auth
def update_strategy_route(strategy_id):
    try:
        return jsonify({"strategy": update_strategy(strategy_id, request.get_json(silent=True) or {}, g.current_user)})
    except Exception as exc:
        return _handle_error(exc)


@strategies_bp.delete("/strategies/<int:strategy_id>")
@require_auth
def delete_strategy_route(strategy_id):
    try:
        delete_strategy(strategy_id, g.current_user)
        return jsonify({"status": "deleted", "strategy_id": strategy_id})
    except Exception as exc:
        return _handle_error(exc)


@strategies_bp.get("/strategies/<int:strategy_id>/versions")
@require_auth
def strategy_versions(strategy_id):
    if not get_strategy(strategy_id):
        return jsonify({"error": "strategy_not_found"}), 404
    return jsonify({"versions": list_strategy_versions(strategy_id)})


@strategies_bp.post("/strategies/<int:strategy_id>/versions")
@require_auth
def create_strategy_version_route(strategy_id):
    try:
        version = create_strategy_version(strategy_id, request.get_json(silent=True) or {}, g.current_user)
        return jsonify({"version": version}), 201
    except Exception as exc:
        return _handle_error(exc)


@strategies_bp.get("/strategy-versions/<int:version_id>")
@require_auth
def strategy_version_detail(version_id):
    version = get_strategy_version(version_id)
    if not version:
        return jsonify({"error": "strategy_version_not_found"}), 404
    return jsonify({"version": version})


@strategies_bp.delete("/strategies/<int:strategy_id>/versions/<int:version_id>")
@require_auth
def delete_strategy_version_route(strategy_id, version_id):
    try:
        delete_strategy_version(strategy_id, version_id, g.current_user)
        return jsonify({"status": "deleted", "version_id": version_id})
    except Exception as exc:
        return _handle_error(exc)


@strategies_bp.post("/strategies/<int:strategy_id>/instruments")
@require_auth
def add_instrument(strategy_id):
    payload = request.get_json(silent=True) or {}
    try:
        instrument_id = int(payload.get("instrument_id") or 0)
        instruments = add_strategy_instrument(strategy_id, instrument_id, g.current_user)
        return jsonify({"instruments": instruments})
    except Exception as exc:
        return _handle_error(exc)


@strategies_bp.delete("/strategies/<int:strategy_id>/instruments/<int:instrument_id>")
@require_auth
def remove_instrument(strategy_id, instrument_id):
    try:
        instruments = remove_strategy_instrument(strategy_id, instrument_id, g.current_user)
        return jsonify({"instruments": instruments})
    except Exception as exc:
        return _handle_error(exc)
