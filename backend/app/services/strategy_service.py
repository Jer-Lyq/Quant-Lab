import ast
import hashlib

from ..db import get_db


STRATEGY_TYPES = {"trend", "mean_reversion", "breakout", "momentum", "timing", "custom"}
FREQUENCIES = {"daily", "weekly"}
STATUSES = {"draft", "ready", "backtesting", "validated", "discarded"}


DEFAULT_RQALPHA_CODE = """def init(context):
    # 初始化策略参数和全局状态
    pass


def handle_bar(context, bar_dict):
    # 每个 bar 调用一次，在这里写交易逻辑
    pass
"""


def validate_rqalpha_code(code):
    if not code or not code.strip():
        return "invalid", "策略代码不能为空"
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return "invalid", f"Python 语法错误：第 {exc.lineno} 行，{exc.msg}"

    function_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    missing = [name for name in ("init", "handle_bar") if name not in function_names]
    if missing:
        return "invalid", f"缺少 RQAlpha 函数：{', '.join(missing)}"
    return "valid", "RQAlpha 基础结构校验通过"


def code_hash(code):
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def can_edit_strategy(strategy, user):
    return user["role"] == "admin" or strategy["author_id"] == user["id"]


def normalize_strategy_payload(payload, existing=None):
    name = (payload.get("name") or (existing["name"] if existing else "")).strip()
    strategy_type = payload.get("strategy_type") or (existing["strategy_type"] if existing else "custom")
    freq = payload.get("freq") or (existing["freq"] if existing else "daily")
    status = payload.get("status") or (existing["status"] if existing else "draft")

    if not name:
        raise ValueError("strategy_name_required")
    if strategy_type not in STRATEGY_TYPES:
        raise ValueError("invalid_strategy_type")
    if freq not in FREQUENCIES:
        raise ValueError("invalid_freq")
    if status not in STATUSES:
        raise ValueError("invalid_strategy_status")

    return {
        "name": name,
        "description": payload.get("description", existing["description"] if existing else None),
        "strategy_idea": payload.get("strategy_idea", existing.get("strategy_idea") if existing else None),
        "uploader_notes": payload.get("uploader_notes", existing["uploader_notes"] if existing else None),
        "strategy_type": strategy_type,
        "market": payload.get("market", existing["market"] if existing else None),
        "freq": freq,
        "status": status,
    }


def row_to_strategy(row):
    return dict(row) if row else None


def list_strategies():
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
        """
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
    db = get_db()
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
    db.commit()
    return get_strategy(cursor.lastrowid)


def update_strategy(strategy_id, payload, user):
    strategy = get_strategy(strategy_id)
    if not strategy:
        raise LookupError("strategy_not_found")
    if not can_edit_strategy(strategy, user):
        raise PermissionError("strategy_edit_denied")

    data = normalize_strategy_payload(payload, strategy)
    db = get_db()
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
    db.commit()
    return get_strategy(strategy_id)


def delete_strategy(strategy_id, user):
    strategy = get_strategy(strategy_id)
    if not strategy:
        raise LookupError("strategy_not_found")
    if not can_edit_strategy(strategy, user):
        raise PermissionError("strategy_delete_denied")
    get_db().execute("DELETE FROM strategies WHERE id = ?", (strategy_id,))
    get_db().commit()


def create_strategy_version(strategy_id, payload, user):
    strategy = get_strategy(strategy_id)
    if not strategy:
        raise LookupError("strategy_not_found")
    if not can_edit_strategy(strategy, user):
        raise PermissionError("strategy_version_denied")

    code = payload.get("code") or DEFAULT_RQALPHA_CODE
    validation_status, validation_message = validate_rqalpha_code(code)
    version_name = (payload.get("version_name") or "").strip()
    if not version_name:
        version_name = next_version_name(strategy_id)

    db = get_db()
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
            payload.get("notes"),
            validation_status,
            validation_message,
            user["id"],
        ),
    )
    db.execute("UPDATE strategies SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (strategy_id,))
    db.commit()
    return get_strategy_version(cursor.lastrowid)


def next_version_name(strategy_id):
    count = get_db().execute(
        "SELECT COUNT(*) AS total FROM strategy_versions WHERE strategy_id = ?",
        (strategy_id,),
    ).fetchone()["total"]
    return f"v{count + 1}"


def list_strategy_versions(strategy_id):
    rows = get_db().execute(
        """
        SELECT sv.*, u.username AS created_by_name
        FROM strategy_versions sv
        LEFT JOIN users u ON u.id = sv.created_by
        WHERE sv.strategy_id = ?
        ORDER BY sv.created_at DESC, sv.id DESC
        """,
        (strategy_id,),
    ).fetchall()
    return [dict(row) for row in rows]


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
    strategy = get_strategy(strategy_id)
    if not strategy:
        raise LookupError("strategy_not_found")
    if not can_edit_strategy(strategy, user):
        raise PermissionError("strategy_version_delete_denied")

    version = get_strategy_version(version_id)
    if not version or version["strategy_id"] != strategy_id:
        raise LookupError("strategy_version_not_found")

    backtest_count = get_db().execute(
        "SELECT COUNT(*) AS total FROM backtest_runs WHERE strategy_version_id = ?",
        (version_id,),
    ).fetchone()["total"]
    if backtest_count:
        raise ValueError("strategy_version_in_use")

    db = get_db()
    db.execute("DELETE FROM strategy_versions WHERE id = ?", (version_id,))
    db.execute("UPDATE strategies SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (strategy_id,))
    db.commit()


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
    strategy = get_strategy(strategy_id)
    if not strategy:
        raise LookupError("strategy_not_found")
    if not can_edit_strategy(strategy, user):
        raise PermissionError("strategy_instrument_denied")

    instrument = get_db().execute("SELECT id FROM instruments WHERE id = ?", (instrument_id,)).fetchone()
    if not instrument:
        raise LookupError("instrument_not_found")
    get_db().execute(
        """
        INSERT OR IGNORE INTO strategy_instruments (strategy_id, instrument_id)
        VALUES (?, ?)
        """,
        (strategy_id, instrument_id),
    )
    get_db().execute("UPDATE strategies SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (strategy_id,))
    get_db().commit()
    return list_strategy_instruments(strategy_id)


def remove_strategy_instrument(strategy_id, instrument_id, user):
    strategy = get_strategy(strategy_id)
    if not strategy:
        raise LookupError("strategy_not_found")
    if not can_edit_strategy(strategy, user):
        raise PermissionError("strategy_instrument_denied")
    get_db().execute(
        "DELETE FROM strategy_instruments WHERE strategy_id = ? AND instrument_id = ?",
        (strategy_id, instrument_id),
    )
    get_db().execute("UPDATE strategies SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (strategy_id,))
    get_db().commit()
    return list_strategy_instruments(strategy_id)


def latest_backtests(strategy_id, limit=5):
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
