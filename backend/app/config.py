import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _cors_origins():
    value = os.getenv("CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173")
    origins = [item.strip() for item in value.split(",") if item.strip()]
    return origins or ["http://127.0.0.1:5173", "http://localhost:5173"]


class Config:
    BASE_DIR = Path(__file__).resolve().parents[1]
    PROJECT_DIR = BASE_DIR.parent
    DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_DIR / "data"))
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "quant_lab.sqlite3"))
    INSTRUMENT_DATA_DIR = os.getenv("INSTRUMENT_DATA_DIR", str(DATA_DIR / "instruments"))
    BACKTEST_DATA_DIR = os.getenv("BACKTEST_DATA_DIR", str(DATA_DIR / "backtests"))
    BACKTEST_RUNNER = os.getenv("BACKTEST_RUNNER", "disabled").strip().lower()
    BACKTEST_WORKER_POLL_SECONDS = max(0.2, min(float(os.getenv("BACKTEST_WORKER_POLL_SECONDS", "1")), 30))
    BACKTEST_TIMEOUT_SECONDS = max(10, min(int(os.getenv("BACKTEST_TIMEOUT_SECONDS", "300")), 3600))
    BACKTEST_JOB_LEASE_SECONDS = max(
        BACKTEST_TIMEOUT_SECONDS + 30,
        min(int(os.getenv("BACKTEST_JOB_LEASE_SECONDS", "600")), 7200),
    )
    BACKTEST_JOB_MAX_ATTEMPTS = max(1, min(int(os.getenv("BACKTEST_JOB_MAX_ATTEMPTS", "2")), 5))
    BACKTEST_DOCKER_IMAGE = os.getenv("BACKTEST_DOCKER_IMAGE", "quant-lab-backtest-runner:latest")
    BACKTEST_HOST_DATA_DIR = os.getenv("BACKTEST_HOST_DATA_DIR", "").strip()
    RQALPHA_BUNDLE_DIR = os.getenv("RQALPHA_BUNDLE_DIR", str(DATA_DIR / "rqalpha-bundle"))
    RQALPHA_HOST_BUNDLE_DIR = os.getenv("RQALPHA_HOST_BUNDLE_DIR", "").strip()
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
    TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")
    TUSHARE_HTTP_URL = os.getenv("TUSHARE_HTTP_URL", "https://tuaremax.top")
    CORS_ORIGINS = _cors_origins()
    SESSION_DAYS = max(1, min(int(os.getenv("SESSION_DAYS", "7")), 30))
    MAX_CONTENT_LENGTH = max(64 * 1024, min(int(os.getenv("MAX_CONTENT_LENGTH", str(1024 * 1024))), 4 * 1024 * 1024))
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me-now")
