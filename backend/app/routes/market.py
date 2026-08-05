from flask import Blueprint, g, jsonify, request

from ..auth import require_auth
from ..db import get_db
from ..services.indicator_service import build_indicators

market_bp = Blueprint("market", __name__)


@market_bp.get("/instruments")
@require_auth
def instruments():
    rows = get_db().execute(
        """
        SELECT id, ts_code, name, asset_type, market, industry, area, is_published,
               status, last_synced_at, updated_at
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
        "SELECT id FROM instruments WHERE id=? AND (is_published=1 OR ?='admin')",
        (instrument_id, g.current_user["role"]),
    ).fetchone()
    if not instrument:
        return []
    return get_db().execute(
        """
        SELECT trade_date, open, high, low, close, volume, amount
        FROM price_bars
        WHERE instrument_id=? AND freq=?
        ORDER BY trade_date ASC
        """,
        (instrument_id, freq),
    ).fetchall()

