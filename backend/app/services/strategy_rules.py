import ast


STRATEGY_TYPES = {"trend", "mean_reversion", "breakout", "momentum", "timing", "custom"}
FREQUENCIES = {"daily", "weekly"}
STATUSES = {"draft", "ready", "backtesting", "validated", "discarded"}
USER_MANAGED_STATUSES = {"draft", "ready", "discarded"}
SYSTEM_MANAGED_STATUSES = {"backtesting", "validated"}

MAX_STRATEGY_NAME_LENGTH = 120
MAX_MARKET_LENGTH = 80
MAX_DESCRIPTION_LENGTH = 4_000
MAX_STRATEGY_IDEA_LENGTH = 8_000
MAX_UPLOADER_NOTES_LENGTH = 4_000
MAX_VERSION_NAME_LENGTH = 80
MAX_VERSION_NOTES_LENGTH = 4_000
MAX_CODE_LENGTH = 256_000

BLOCKED_IMPORT_ROOTS = {
    "builtins",
    "ctypes",
    "http",
    "importlib",
    "marshal",
    "multiprocessing",
    "os",
    "pathlib",
    "pickle",
    "requests",
    "shelve",
    "shutil",
    "socket",
    "subprocess",
    "sys",
    "threading",
    "urllib",
}
BLOCKED_CALLS = {
    "__import__",
    "breakpoint",
    "compile",
    "delattr",
    "eval",
    "exec",
    "getattr",
    "globals",
    "input",
    "locals",
    "open",
    "setattr",
    "vars",
}


class StrategyError(Exception):
    status_code = 400

    def __init__(self, code):
        super().__init__(code)
        self.code = code


class StrategyNotFoundError(StrategyError):
    status_code = 404


class StrategyPermissionError(StrategyError):
    status_code = 403


class StrategyConflictError(StrategyError):
    status_code = 409


def require_object_payload(payload):
    if not isinstance(payload, dict):
        raise StrategyError("json_object_required")
    return payload


def _read_text(payload, field, *, default=None, required=False, max_length=None):
    if field not in payload:
        value = default
    else:
        value = payload[field]

    if value is None:
        if required:
            raise StrategyError(f"{field}_required")
        return None
    if not isinstance(value, str):
        raise StrategyError(f"invalid_{field}_type")

    value = value.strip()
    if required and not value:
        raise StrategyError(f"{field}_required")
    if max_length is not None and len(value) > max_length:
        raise StrategyError(f"{field}_too_long")
    return value


def normalize_strategy_payload(payload, existing=None):
    require_object_payload(payload)
    existing = existing or {}

    name = _read_text(
        payload,
        "name",
        default=existing.get("name"),
        required=True,
        max_length=MAX_STRATEGY_NAME_LENGTH,
    )
    strategy_type = payload.get("strategy_type", existing.get("strategy_type", "custom"))
    freq = payload.get("freq", existing.get("freq", "daily"))
    status = payload.get("status", existing.get("status", "draft"))

    if not isinstance(strategy_type, str) or strategy_type not in STRATEGY_TYPES:
        raise StrategyError("invalid_strategy_type")
    if not isinstance(freq, str) or freq not in FREQUENCIES:
        raise StrategyError("invalid_freq")
    if not isinstance(status, str) or status not in STATUSES:
        raise StrategyError("invalid_strategy_status")

    return {
        "name": name,
        "description": _read_text(
            payload,
            "description",
            default=existing.get("description"),
            max_length=MAX_DESCRIPTION_LENGTH,
        ),
        "strategy_idea": _read_text(
            payload,
            "strategy_idea",
            default=existing.get("strategy_idea"),
            max_length=MAX_STRATEGY_IDEA_LENGTH,
        ),
        "uploader_notes": _read_text(
            payload,
            "uploader_notes",
            default=existing.get("uploader_notes"),
            max_length=MAX_UPLOADER_NOTES_LENGTH,
        ),
        "strategy_type": strategy_type,
        "market": _read_text(
            payload,
            "market",
            default=existing.get("market"),
            max_length=MAX_MARKET_LENGTH,
        ),
        "freq": freq,
        "status": status,
    }


def normalize_version_payload(payload, default_code):
    require_object_payload(payload)
    code = payload.get("code", default_code)
    if not isinstance(code, str):
        raise StrategyError("invalid_strategy_code_type")
    if not code.strip():
        raise StrategyError("strategy_code_required")
    if len(code) > MAX_CODE_LENGTH:
        raise StrategyError("strategy_code_too_long")

    return {
        "version_name": _read_text(
            payload,
            "version_name",
            default="",
            max_length=MAX_VERSION_NAME_LENGTH,
        ),
        "notes": _read_text(
            payload,
            "notes",
            max_length=MAX_VERSION_NOTES_LENGTH,
        ),
        "code": code,
    }


def validate_status_change(data, existing, user):
    if user["role"] == "admin":
        return
    previous_status = existing.get("status") if existing else None
    status_changed = data["status"] != previous_status
    if status_changed and (
        data["status"] not in USER_MANAGED_STATUSES or previous_status in SYSTEM_MANAGED_STATUSES
    ):
        raise StrategyPermissionError("strategy_status_transition_denied")


def _top_level_functions(tree):
    functions = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if node.name in functions:
                return None, f"策略函数重复定义：{node.name}"
            functions[node.name] = node
    return functions, None


def _validate_required_signature(function, expected_arguments):
    positional = [*function.args.posonlyargs, *function.args.args]
    if len(positional) < expected_arguments:
        return False
    return True


def validate_rqalpha_code(code):
    if not isinstance(code, str) or not code.strip():
        return "invalid", "策略代码不能为空"
    if len(code) > MAX_CODE_LENGTH:
        return "invalid", f"策略代码不能超过 {MAX_CODE_LENGTH} 个字符"

    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError) as exc:
        line = getattr(exc, "lineno", None)
        location = f"第 {line} 行，" if line else ""
        return "invalid", f"Python 语法错误：{location}{exc}"

    functions, function_error = _top_level_functions(tree)
    if function_error:
        return "invalid", function_error

    missing = [name for name in ("init", "handle_bar") if name not in functions]
    if missing:
        return "invalid", f"缺少顶层 RQAlpha 函数：{', '.join(missing)}"
    if not _validate_required_signature(functions["init"], 1):
        return "invalid", "init 至少需要 context 参数"
    if not _validate_required_signature(functions["handle_bar"], 2):
        return "invalid", "handle_bar 至少需要 context 和 bar_dict 参数"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = {alias.name.split(".", 1)[0] for alias in node.names}
            blocked = roots & BLOCKED_IMPORT_ROOTS
            if blocked:
                return "invalid", f"禁止导入高风险模块：{', '.join(sorted(blocked))}"
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root in BLOCKED_IMPORT_ROOTS:
                return "invalid", f"禁止导入高风险模块：{root}"
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in BLOCKED_CALLS:
            return "invalid", f"禁止调用高风险函数：{node.func.id}"
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return "invalid", "禁止访问双下划线内部属性"

    return "valid", "RQAlpha 基础结构与静态安全校验通过"
