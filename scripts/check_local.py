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
    strategy = client.post(
        "/api/strategies",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "双均线示例策略",
            "description": "本地检查用策略",
            "strategy_idea": "用短长均线交叉记录趋势切换，作为策略研究的起点。",
            "strategy_type": "trend",
            "freq": "daily",
            "status": "draft",
        },
    )
    assert strategy.status_code == 201, strategy.json
    strategy_id = strategy.json["strategy"]["id"]
    assert strategy.json["strategy"]["strategy_idea"] == "用短长均线交叉记录趋势切换，作为策略研究的起点。"
    version = client.post(
        f"/api/strategies/{strategy_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "version_name": "v1-check",
            "code": "def init(context):\n    pass\n\n\ndef handle_bar(context, bar_dict):\n    pass\n",
            "notes": "结构校验应该通过",
        },
    )
    assert version.status_code == 201, version.json
    assert version.json["version"]["validation_status"] == "valid", version.json
    detail = client.get(
        f"/api/strategies/{strategy_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail.status_code == 200, detail.json
    assert len(detail.json["versions"]) == 1, detail.json
    deleted_version = client.delete(
        f"/api/strategies/{strategy_id}/versions/{version.json['version']['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert deleted_version.status_code == 200, deleted_version.json
    detail_after_delete = client.get(
        f"/api/strategies/{strategy_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_after_delete.status_code == 200, detail_after_delete.json
    assert not detail_after_delete.json["versions"], detail_after_delete.json
    print("Quant Lab local check passed.")


if __name__ == "__main__":
    main()
