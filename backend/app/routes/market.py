from flask import Blueprint, g, jsonify, request

from ..auth import require_auth
from ..db import get_db
from ..engine.market_engine import build_indicators, build_market_snapshot
from ..services.dataset_store import read_ohlcv_bars

market_bp = Blueprint("market", __name__)


@market_bp.get("/instruments")
@require_auth
def instruments():
    rows = get_db().execute(
        """
        SELECT id, ts_code, name, asset_type, market, industry, area, data_start, data_end,
               is_published, status, last_synced_at, updated_at
        FROM instruments
        WHERE is_published=1 OR ?='admin'
        ORDER BY updated_at DESC
        """,
        (g.current_user["role"],),
    ).fetchall()
    return jsonify({"instruments": [dict(row) for row in rows]})


@market_bp.get("/instruments/<int:instrument_id>")
@require_auth
def instrument_detail(instrument_id):
    row = get_db().execute(
        """
        SELECT *
        FROM instruments
        WHERE id=? AND (is_published=1 OR ?='admin')
        """,
        (instrument_id, g.current_user["role"]),
    ).fetchone()
    if not row:
        return jsonify({"error": "instrument_not_found"}), 404
    return jsonify({"instrument": dict(row)})


@market_bp.get("/instruments/<int:instrument_id>/bars")
@require_auth
def bars(instrument_id):
    freq = request.args.get("freq", "daily")
    if freq not in {"daily", "weekly"}:
        return jsonify({"error": "invalid_freq"}), 400
    rows = _bars_for(instrument_id, freq)
    return jsonify({"bars": [dict(row) for row in rows]})


@market_bp.get("/instruments/<int:instrument_id>/indicators")
@require_auth
def indicators(instrument_id):
    freq = request.args.get("freq", "daily")
    if freq not in {"daily", "weekly"}:
        return jsonify({"error": "invalid_freq"}), 400
    rows = [dict(row) for row in _bars_for(instrument_id, freq)]
    return jsonify({"indicators": build_indicators(rows)})


@market_bp.get("/instruments/<int:instrument_id>/analytics")
@require_auth
def analytics(instrument_id):
    freq = request.args.get("freq", "daily")
    if freq not in {"daily", "weekly"}:
        return jsonify({"error": "invalid_freq"}), 400
    rows = [dict(row) for row in _bars_for(instrument_id, freq)]
    return jsonify(build_market_snapshot(rows))


@market_bp.post("/research-requests")
@require_auth
def research_request():
    payload = request.get_json(silent=True) or {}
    ts_code = (payload.get("ts_code") or "").upper().strip()
    asset_type = payload.get("asset_type") or "stock"
    if not ts_code:
        return jsonify({"error": "ts_code_required"}), 400
    if asset_type not in {"stock", "etf", "fund"}:
        return jsonify({"error": "invalid_asset_type"}), 400
    cursor = get_db().execute(
        """
        INSERT INTO research_requests (user_id, ts_code, asset_type, reason)
        VALUES (?, ?, ?, ?)
        """,
        (g.current_user["id"], ts_code, asset_type, payload.get("reason")),
    )
    get_db().commit()
    return jsonify({"id": cursor.lastrowid, "status": "pending"}), 201


def _bars_for(instrument_id, freq):
    instrument = get_db().execute(
        """
        SELECT id, ts_code, asset_type
        FROM instruments
        WHERE id=? AND (is_published=1 OR ?='admin')
        """,
        (instrument_id, g.current_user["role"]),
    ).fetchone()
    if not instrument:
        return []
    return read_ohlcv_bars(instrument, freq)
