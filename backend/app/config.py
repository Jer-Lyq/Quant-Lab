import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    BASE_DIR = Path(__file__).resolve().parents[1]
    PROJECT_DIR = BASE_DIR.parent
    DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_DIR / "data"))
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "quant_lab.sqlite3"))
    INSTRUMENT_DATA_DIR = os.getenv("INSTRUMENT_DATA_DIR", str(DATA_DIR / "instruments"))
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
    TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")
    TUSHARE_HTTP_URL = os.getenv("TUSHARE_HTTP_URL", "https://tuaremax.top")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    SESSION_DAYS = int(os.getenv("SESSION_DAYS", "7"))
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me-now")
