import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import get_db


def utc_now():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.replace(microsecond=0).isoformat()


def create_user(username, password, role="user"):
    db = get_db()
    password_hash = generate_password_hash(password)
    cursor = db.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, password_hash, role),
    )
    db.commit()
    return get_user_by_id(cursor.lastrowid)


def create_admin_from_env():
    username = current_app.config["ADMIN_USERNAME"]
    password = current_app.config["ADMIN_PASSWORD"]
    existing = get_user_by_username(username)
    if existing:
        return existing
    return create_user(username, password, "admin")


def get_user_by_username(username):
    row = get_db().execute(
        "SELECT id, username, role, created_at FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    return dict(row) if row else None


def get_user_with_password(username):
    row = get_db().execute(
        "SELECT id, username, password_hash, role, created_at FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id):
    row = get_db().execute(
        "SELECT id, username, role, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return dict(row) if row else None


def login(username, password):
    user = get_user_with_password(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return None
    token = secrets.token_urlsafe(32)
    expires_at = utc_now() + timedelta(days=current_app.config["SESSION_DAYS"])
    get_db().execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user["id"], iso(expires_at)),
    )
    get_db().commit()
    return {
        "token": token,
        "user": {"id": user["id"], "username": user["username"], "role": user["role"]},
        "expires_at": iso(expires_at),
    }


def resolve_token(token):
    if not token:
        return None
    row = get_db().execute(
        """
        SELECT s.token, s.expires_at, u.id, u.username, u.role
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token = ?
        """,
        (token,),
    ).fetchone()
    if not row:
        return None
    expires_at = datetime.fromisoformat(row["expires_at"])
    if expires_at < utc_now():
        get_db().execute("DELETE FROM sessions WHERE token = ?", (token,))
        get_db().commit()
        return None
    return {"id": row["id"], "username": row["username"], "role": row["role"]}

