from flask import Blueprint, jsonify, request

from ..auth import require_auth
from ..services.auth_service import login

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/login")
def login_route():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    result = login(username, password)
    if not result:
        return jsonify({"error": "invalid_credentials"}), 401
    return jsonify(result)


@auth_bp.get("/me")
@require_auth
def me():
    from flask import g

    return jsonify({"user": g.current_user})

