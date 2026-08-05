from ..db import get_db

TUSHARE_TOKEN_KEY = "tushare_token"
TUSHARE_HTTP_URL_KEY = "tushare_http_url"


def ensure_settings_table():
    get_db().execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def get_setting(key):
    ensure_settings_table()
    row = get_db().execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(key, value):
    ensure_settings_table()
    get_db().execute(
        """
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value=excluded.value,
            updated_at=CURRENT_TIMESTAMP
        """,
        (key, value),
    )
    get_db().commit()


def get_tushare_token():
    from flask import current_app

    return get_setting(TUSHARE_TOKEN_KEY) or current_app.config.get("TUSHARE_TOKEN", "")


def get_tushare_http_url():
    from flask import current_app

    return get_setting(TUSHARE_HTTP_URL_KEY) or current_app.config.get("TUSHARE_HTTP_URL", "https://tuaremax.top")


def get_tushare_connection_meta():
    from flask import current_app

    ensure_settings_table()
    token_row = get_db().execute(
        "SELECT value, updated_at FROM app_settings WHERE key=?",
        (TUSHARE_TOKEN_KEY,),
    ).fetchone()
    url_row = get_db().execute(
        "SELECT value, updated_at FROM app_settings WHERE key=?",
        (TUSHARE_HTTP_URL_KEY,),
    ).fetchone()
    token_value = token_row["value"] if token_row and token_row["value"] else current_app.config.get("TUSHARE_TOKEN", "")
    url_value = url_row["value"] if url_row and url_row["value"] else current_app.config.get("TUSHARE_HTTP_URL", "https://tuaremax.top")
    source = "database" if (token_row and token_row["value"]) or (url_row and url_row["value"]) else ("environment" if token_value or url_value else None)
    return {
        "configured": bool(token_value),
        "source": source,
        "token_masked": mask_secret(token_value),
        "http_url": url_value,
        "updated_at": token_row["updated_at"] if token_row and token_row["value"] else (url_row["updated_at"] if url_row and url_row["value"] else None),
    }


def mask_secret(value):
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * max(4, len(value) - 8)}{value[-4:]}"
