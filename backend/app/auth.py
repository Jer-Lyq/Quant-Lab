from functools import wraps

from flask import g, jsonify, request

from .services.auth_service import resolve_token


def current_token():
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header.removeprefix("Bearer ").strip()
    return request.headers.get("X-Auth-Token")


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = resolve_token(current_token())
        if not user:
            return jsonify({"error": "authentication_required"}), 401
        g.current_user = user
        return view(*args, **kwargs)

    return wrapped


def require_admin(view):
    @wraps(view)
    @require_auth
    def wrapped(*args, **kwargs):
        if g.current_user["role"] != "admin":
            return jsonify({"error": "admin_required"}), 403
        return view(*args, **kwargs)

    return wrapped

