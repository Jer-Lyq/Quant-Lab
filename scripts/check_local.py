from pathlib import Path
import os
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def require_file(path):
    if not path.exists():
        raise AssertionError(f"missing required file: {path.relative_to(ROOT)}")


def main():
    for relative in [
        "docker-compose.yml",
        ".env.example",
        "nginx/quant-lab.conf",
        "backend/Dockerfile",
        "backend/requirements.txt",
        "frontend/Dockerfile",
        "frontend/package.json",
        "deploy/server-setup.md",
    ]:
        require_file(ROOT / relative)

    sys.path.insert(0, str(BACKEND))
    db_path = Path(tempfile.gettempdir()) / "quant_lab_check.sqlite3"
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_PATH"] = str(db_path)
    os.environ["SECRET_KEY"] = "local-check-secret"
    os.environ["ADMIN_USERNAME"] = "admin"
    os.environ["ADMIN_PASSWORD"] = "admin123456"

    from app import create_app
    from app.db import init_db
    from app.services.auth_service import create_admin_from_env

    app = create_app()
    with app.app_context():
        init_db()
        create_admin_from_env()

    client = app.test_client()
    assert client.get("/api/health").status_code == 200
    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123456"},
    )
    assert login.status_code == 200, login.json
    token = login.json["token"]
    instruments = client.get(
        "/api/instruments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert instruments.status_code == 200, instruments.json
    print("Quant Lab local check passed.")


if __name__ == "__main__":
    main()

