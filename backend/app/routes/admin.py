from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from ..auth import require_admin
from ..db import get_db
from ..services.auth_service import create_user
from ..services.settings_service import (
    TUSHARE_HTTP_URL_KEY,
    TUSHARE_TOKEN_KEY,
    get_tushare_connection_meta,
    set_setting,
)
from ..services.tushare_service import fetch_bars, fetch_basic_info

admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/data-source")
@require_admin
def data_source():
    return jsonify({"provider": "tushare", "connection": get_tushare_connection_meta()})


@admin_bp.patch("/data-source")
@require_admin
def update_data_source():
    payload = request.get_json(silent=True) or {}
    token = (payload.get("tushare_token") or payload.get("token") or "").strip()
    http_url = (payload.get("tushare_http_url") or payload.get("http_url") or "").strip()
    if not token and not http_url:
        return jsonify({"error": "tushare_token_or_http_url_required"}), 400
    if token:
        set_setting(TUSHARE_TOKEN_KEY, token)
    if http_url:
        set_setting(TUSHARE_HTTP_URL_KEY, http_url)
    return jsonify({"provider": "tushare", "connection": get_tushare_connection_meta()})


@admin_bp.post("/users")
@require_admin
def create_normal_user():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    if not username or not password:
        return jsonify({"error": "username_and_password_required"}), 400
    try:
        user = create_user(username, password, "user")
        return jsonify({"user": user}), 201
    except Exception as exc:
        return jsonify({"error": "create_user_failed", "message": str(exc)}), 400


@admin_bp.post("/instruments")
@require_admin
def create_instrument():
    payload = request.get_json(silent=True) or {}
    ts_code = (payload.get("ts_code") or "").upper().strip()
    asset_type = payload.get("asset_type") or "stock"
    if not ts_code:
        return jsonify({"error": "ts_code_required"}), 400
    if asset_type not in {"stock", "etf", "fund"}:
        return jsonify({"error": "invalid_asset_type"}), 400

    info = fetch_basic_info(ts_code, asset_type)
    db = get_db()
    db.execute(
        """
        INSERT INTO instruments
        (ts_code, name, asset_type, market, industry, area, list_date, data_start, data_end, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ts_code) DO UPDATE SET
            name=excluded.name,
            asset_type=excluded.asset_type,
            market=excluded.market,
            industry=excluded.industry,
            area=excluded.area,
            list_date=excluded.list_date,
            data_start=excluded.data_start,
            data_end=excluded.data_end,
            notes=excluded.notes,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            ts_code,
            payload.get("name") or info.get("name") or ts_code,
            asset_type,
            info.get("market"),
            info.get("industry"),
            info.get("area"),
            info.get("list_date"),
            payload.get("data_start"),
            payload.get("data_end"),
            payload.get("notes"),
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM instruments WHERE ts_code = ?", (ts_code,)).fetchone()
    return jsonify({"instrument": dict(row)}), 201


@admin_bp.post("/instruments/<int:instrument_id>/sync")
@require_admin
def sync_instrument(instrument_id):
    payload = request.get_json(silent=True) or {}
    db = get_db()
    instrument = db.execute("SELECT * FROM instruments WHERE id = ?", (instrument_id,)).fetchone()
    if not instrument:
        return jsonify({"error": "instrument_not_found"}), 404

    started_log = db.execute(
        "INSERT INTO sync_logs (instrument_id, status, message) VALUES (?, ?, ?)",
        (instrument_id, "running", "sync started"),
    )
    db.commit()
    log_id = started_log.lastrowid

    try:
        requested_end_date = (payload.get("end_date") or payload.get("data_end") or "").strip()
        effective_end_date = requested_end_date or datetime.now(timezone.utc).strftime("%Y%m%d")
        total_rows = 0
        for freq in ("daily", "weekly"):
            rows = fetch_bars(
                instrument["ts_code"],
                instrument["asset_type"],
                freq,
                instrument["data_start"],
                effective_end_date,
            )
            for row in rows:
                db.execute(
                    """
                    INSERT INTO price_bars
                    (instrument_id, freq, trade_date, open, high, low, close, volume, amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(instrument_id, freq, trade_date) DO UPDATE SET
                        open=excluded.open,
                        high=excluded.high,
                        low=excluded.low,
                        close=excluded.close,
                        volume=excluded.volume,
                        amount=excluded.amount
                    """,
                    (
                        instrument_id,
                        freq,
                        row["trade_date"],
                        row["open"],
                        row["high"],
                        row["low"],
                        row["close"],
                        row["volume"],
                        row["amount"],
                    ),
                )
            total_rows += len(rows)

        if total_rows == 0:
            raise RuntimeError("Tushare returned no rows for this instrument.")

        db.execute(
            """
            UPDATE instruments
            SET status='ready', is_published=1, last_synced_at=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (datetime.now(timezone.utc).replace(microsecond=0).isoformat(), instrument_id),
        )
        db.execute(
            "UPDATE sync_logs SET status=?, message=?, rows_synced=?, finished_at=CURRENT_TIMESTAMP WHERE id=?",
            ("success", "sync completed", total_rows, log_id),
        )
        db.commit()
        return jsonify({"status": "success", "rows_synced": total_rows})
    except Exception as exc:
        db.execute(
            "UPDATE sync_logs SET status=?, message=?, finished_at=CURRENT_TIMESTAMP WHERE id=?",
            ("failed", str(exc), log_id),
        )
        db.commit()
        return jsonify({"error": "sync_failed", "message": str(exc)}), 500


@admin_bp.patch("/instruments/<int:instrument_id>")
@require_admin
def update_instrument(instrument_id):
    payload = request.get_json(silent=True) or {}
    is_published = 1 if payload.get("is_published") else 0
    status = "ready" if is_published else "draft"
    db = get_db()
    db.execute(
        "UPDATE instruments SET is_published=?, status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (is_published, status, instrument_id),
    )
    db.commit()
    return jsonify({"status": "ok"})
