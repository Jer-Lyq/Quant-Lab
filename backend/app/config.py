import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    BASE_DIR = Path(__file__).resolve().parents[1]
    DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "quant_lab.sqlite3"))
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
    TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    SESSION_DAYS = int(os.getenv("SESSION_DAYS", "7"))
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me-now")

