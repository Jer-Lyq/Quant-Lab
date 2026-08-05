from flask import Flask
from flask_cors import CORS

from .config import Config
from .db import close_db, init_db
from .routes.admin import admin_bp
from .routes.auth import auth_bp
from .routes.market import market_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    app.teardown_appcontext(close_db)

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(market_bp, url_prefix="/api")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "quant-lab"}

    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        print("Initialized Quant Lab database.")

    @app.cli.command("create-admin")
    def create_admin_command():
        from .services.auth_service import create_admin_from_env

        init_db()
        user = create_admin_from_env()
        print(f"Admin user ready: {user['username']}")

    return app

