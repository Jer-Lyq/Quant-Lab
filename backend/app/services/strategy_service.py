import hashlib
import re

from ..db import get_db
from .strategy_rules import (
    StrategyConflictError,
    StrategyError,
    StrategyNotFoundError,
    StrategyPermissionError,
    normalize_strategy_payload,
    normalize_version_payload,
    validate_rqalpha_code,
    validate_status_change,
)


DEFAULT_RQALPHA_CODE = """def init(context):
    # 初始化策略参数和全局状态
    pass


def handle_bar(context, bar_dict):
    # 每个 bar 调用一次，在这里写交易逻辑
    pass
"""


def code_hash(code):
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def can_edit_strategy(strategy, user):
    return user["role"] == "admin" or strategy["author_id"] == user["id"]


def require_editable_strategy(strategy_id, user, denied_code):
    strategy = get_strategy(strategy_id)
    if not strategy:
        raise StrategyNotFoundError("strategy_not_found")
    if not can_edit_strategy(strategy, user):
        raise StrategyPermissionError(denied_code)
    return strategy


def require_writable_strategy(strategy):
    if strategy["status"] == "discarded":
        raise StrategyConflictError("discarded_strategy_read_only")
    if strategy["status"] == "backtesting":
        raise StrategyConflictError("strategy_backtest_in_progress")


def require_user_mutable_system_status(strategy, user):
    if user["role"] != "admin" and strategy["status"] in {"backtesting", "validated"}:
        raise StrategyPermissionError("system_managed_strategy_read_only")


def require_valid_version_for_status(strategy_id, status):
    if status not in {"ready", "backtesting", "validated"}:
        return
    latest = get_db().execute(
        """
        SELECT validation_status
        FROM strategy_versions
        WHERE strategy_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (strategy_id,),
    ).fetchone()
    if not latest or latest["validation_status"] != "valid":
        raise StrategyConflictError("strategy_valid_version_required")


def row_to_strategy(row):
    return dict(row) if row else None


def list_strategies(limit=500):
    limit = max(1, min(int(limit), 500))
    rows = get_db().execute(
        """
        SELECT s.*,
               u.username AS author_name,
               latest.id AS latest_version_id,
               latest.version_name AS latest_version_name,
               latest.validation_status AS latest_validation_status,
               latest.created_at AS latest_version_created_at,
               COUNT(DISTINCT si.instrument_id) AS instrument_count,
               COUNT(DISTINCT br.id) AS backtest_count
        FROM strategies s
        LEFT JOIN users u ON u.id = s.author_id
        LEFT JOIN strategy_versions latest ON latest.id = (
            SELECT sv.id
            FROM strategy_versions sv
            WHERE sv.strategy_id = s.id
            ORDER BY sv.created_at DESC, sv.id DESC
            LIMIT 1
        )
        LEFT JOIN strategy_instruments si ON si.strategy_id = s.id
        LEFT JOIN backtest_runs br ON br.strategy_id = s.id
        GROUP BY s.id
        ORDER BY s.updated_at DESC, s.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_strategy(strategy_id):
    row = get_db().execute(
        """
        SELECT s.*, u.username AS author_name
        FROM strategies s
        LEFT JOIN users u ON u.id = s.author_id
        WHERE s.id = ?
        """,
        (strategy_id,),
    ).fetchone()
    return row_to_strategy(row)


def create_strategy(payload, user):
    data = normalize_strategy_payload(payload)
    validate_status_change(data, None, user)
    if data["status"] != "draft":
        raise StrategyConflictError("new_strategy_must_start_as_draft")
    db = get_db()
    with db:
        cursor = db.execute(
            """
            INSERT INTO strategies
            (name, description, strategy_idea, uploader_notes, strategy_type, market, freq, status, author_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["name"],
                data["description"],
                data["strategy_idea"],
                data["uploader_notes"],
                data["strategy_type"],
                data["market"],
                data["freq"],
                data["status"],
                user["id"],
            ),
        )
    return get_strategy(cursor.lastrowid)


def update_strategy(strategy_id, payload, user):
    strategy = require_editable_strategy(strategy_id, user, "strategy_edit_denied")
    require_user_mutable_system_status(strategy, user)
    data = normalize_strategy_payload(payload, strategy)
    validate_status_change(data, strategy, user)
    require_valid_version_for_status(strategy_id, data["status"])
    db = get_db()
    with db:
        db.execute(
            """
            UPDATE strategies
            SET name=?,
                description=?,
                strategy_idea=?,
                uploader_notes=?,
                strategy_type=?,
                market=?,
                freq=?,
                status=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                data["name"],
                data["description"],
                data["strategy_idea"],
                data["uploader_notes"],
                data["strategy_type"],
                data["market"],
                data["freq"],
                data["status"],
                strategy_id,
            ),
        )
    return get_strategy(strategy_id)


def delete_strategy(strategy_id, user):
    strategy = require_editable_strategy(strategy_id, user, "strategy_delete_denied")
    require_user_mutable_system_status(strategy, user)
    if strategy["status"] == "backtesting":
        raise StrategyConflictError("strategy_backtest_in_progress")
    db = get_db()
    backtest_count = db.execute(
        "SELECT COUNT(*) AS total FROM backtest_runs WHERE strategy_id = ?",
        (strategy_id,),
    ).fetchone()["total"]
    if backtest_count:
        raise StrategyConflictError("strategy_has_backtest_history")
    with db:
        db.execute("DELETE FROM strategies WHERE id = ?", (strategy_id,))


def create_strategy_version(strategy_id, payload, user):
    strategy = require_editable_strategy(strategy_id, user, "strategy_version_denied")
    require_user_mutable_system_status(strategy, user)
    require_writable_strategy(strategy)
    data = normalize_version_payload(payload, DEFAULT_RQALPHA_CODE)
    code = data["code"]
    validation_status, validation_message = validate_rqalpha_code(code)
    version_name = data["version_name"]
    if not version_name:
        version_name = next_version_name(strategy_id)

    db = get_db()
    duplicate = db.execute(
        "SELECT 1 FROM strategy_versions WHERE strategy_id = ? AND version_name = ?",
        (strategy_id, version_name),
    ).fetchone()
    if duplicate:
        raise StrategyConflictError("strategy_version_name_exists")

    with db:
        cursor = db.execute(
            """
            INSERT INTO strategy_versions
            (strategy_id, version_name, code, code_hash, notes, validation_status, validation_message, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                strategy_id,
                version_name,
                code,
                code_hash(code),
                data["notes"],
                validation_status,
                validation_message,
                user["id"],
            ),
        )
        db.execute(
            """
            UPDATE strategies
            SET status=CASE WHEN status IN ('ready', 'validated') THEN 'draft' ELSE status END,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (strategy_id,),
        )
    return get_strategy_version(cursor.lastrowid)


def next_version_name(strategy_id):
    rows = get_db().execute(
        "SELECT version_name FROM strategy_versions WHERE strategy_id = ?",
        (strategy_id,),
    ).fetchall()
    version_numbers = []
    for row in rows:
        match = re.fullmatch(r"v(\d+)", row["version_name"], flags=re.IGNORECASE)
        if match:
            version_numbers.append(int(match.group(1)))
    return f"v{max(version_numbers, default=0) + 1}"


def list_strategy_versions(strategy_id, limit=100):
    limit = max(1, min(int(limit), 100))
    rows = get_db().execute(
        """
        SELECT sv.id,
               sv.strategy_id,
               sv.version_name,
               sv.code_hash,
               sv.notes,
               sv.validation_status,
               sv.validation_message,
               sv.created_by,
               sv.created_at,
               u.username AS created_by_name
        FROM strategy_versions sv
        LEFT JOIN users u ON u.id = sv.created_by
        WHERE sv.strategy_id = ?
        ORDER BY sv.created_at DESC, sv.id DESC
        LIMIT ?
        """,
        (strategy_id, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def count_strategy_versions(strategy_id):
    return get_db().execute(
        "SELECT COUNT(*) AS total FROM strategy_versions WHERE strategy_id = ?",
        (strategy_id,),
    ).fetchone()["total"]


def get_strategy_version(version_id):
    row = get_db().execute(
        """
        SELECT sv.*, u.username AS created_by_name
        FROM strategy_versions sv
        LEFT JOIN users u ON u.id = sv.created_by
        WHERE sv.id = ?
        """,
        (version_id,),
    ).fetchone()
    return dict(row) if row else None


def delete_strategy_version(strategy_id, version_id, user):
    strategy = require_editable_strategy(strategy_id, user, "strategy_version_delete_denied")
    require_user_mutable_system_status(strategy, user)
    require_writable_strategy(strategy)

    version = get_strategy_version(version_id)
    if not version or version["strategy_id"] != strategy_id:
        raise StrategyNotFoundError("strategy_version_not_found")

    backtest_count = get_db().execute(
        "SELECT COUNT(*) AS total FROM backtest_runs WHERE strategy_version_id = ?",
        (version_id,),
    ).fetchone()["total"]
    if backtest_count:
        raise StrategyConflictError("strategy_version_in_use")

    db = get_db()
    with db:
        db.execute("DELETE FROM strategy_versions WHERE id = ?", (version_id,))
        db.execute(
            """
            UPDATE strategies
            SET status=CASE WHEN status IN ('ready', 'validated') THEN 'draft' ELSE status END,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (strategy_id,),
        )


def list_strategy_instruments(strategy_id):
    rows = get_db().execute(
        """
        SELECT i.*
        FROM strategy_instruments si
        JOIN instruments i ON i.id = si.instrument_id
        WHERE si.strategy_id = ?
        ORDER BY i.name ASC, i.ts_code ASC
        """,
        (strategy_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def add_strategy_instrument(strategy_id, instrument_id, user):
    strategy = require_editable_strategy(strategy_id, user, "strategy_instrument_denied")
    require_user_mutable_system_status(strategy, user)
    require_writable_strategy(strategy)
    if not isinstance(instrument_id, int) or instrument_id <= 0:
        raise StrategyError("invalid_instrument_id")

    instrument = get_db().execute("SELECT id FROM instruments WHERE id = ?", (instrument_id,)).fetchone()
    if not instrument:
        raise StrategyNotFoundError("instrument_not_found")
    db = get_db()
    with db:
        db.execute(
            """
            INSERT OR IGNORE INTO strategy_instruments (strategy_id, instrument_id)
            VALUES (?, ?)
            """,
            (strategy_id, instrument_id),
        )
        db.execute("UPDATE strategies SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (strategy_id,))
    return list_strategy_instruments(strategy_id)


def remove_strategy_instrument(strategy_id, instrument_id, user):
    strategy = require_editable_strategy(strategy_id, user, "strategy_instrument_denied")
    require_user_mutable_system_status(strategy, user)
    require_writable_strategy(strategy)
    db = get_db()
    with db:
        db.execute(
            "DELETE FROM strategy_instruments WHERE strategy_id = ? AND instrument_id = ?",
            (strategy_id, instrument_id),
        )
        db.execute("UPDATE strategies SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (strategy_id,))
    return list_strategy_instruments(strategy_id)


def latest_backtests(strategy_id, limit=5):
    limit = max(1, min(int(limit), 20))
    rows = get_db().execute(
        """
        SELECT br.*, i.ts_code, i.name AS instrument_name, sv.version_name
        FROM backtest_runs br
        LEFT JOIN instruments i ON i.id = br.instrument_id
        LEFT JOIN strategy_versions sv ON sv.id = br.strategy_version_id
        WHERE br.strategy_id = ?
        ORDER BY br.created_at DESC, br.id DESC
        LIMIT ?
        """,
        (strategy_id, limit),
    ).fetchall()
    return [dict(row) for row in rows]
