import os
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def assert_error(response, status, code):
    assert response.status_code == status, response.get_json()
    assert response.get_json() == {"error": code}, response.get_json()


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def login(client, username, password):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.get_json()
    return response.get_json()["token"]


def valid_code():
    return "def init(context):\n    pass\n\n\ndef handle_bar(context, bar_dict):\n    pass\n"


@contextmanager
def temporary_database():
    check_root = ROOT / "data" / "checks"
    check_root.mkdir(parents=True, exist_ok=True)
    db_path = check_root / f"strategy-{uuid.uuid4().hex}.sqlite3"
    try:
        yield db_path
    finally:
        for suffix in ("", "-shm", "-wal"):
            Path(f"{db_path}{suffix}").unlink(missing_ok=True)


def main():
    sys.path.insert(0, str(BACKEND))
    with temporary_database() as db_path:
        os.environ["DATABASE_PATH"] = str(db_path)
        os.environ["SECRET_KEY"] = "strategy-check-secret"
        os.environ["ADMIN_USERNAME"] = "admin"
        os.environ["ADMIN_PASSWORD"] = "admin-check-password"
        os.environ["CORS_ORIGINS"] = "http://127.0.0.1:5173"

        from app import create_app
        from app.db import get_db, init_db
        from app.services.auth_service import create_admin_from_env, create_user

        app = create_app()
        with app.app_context():
            init_db()
            create_admin_from_env()
            create_user("author", "author-check-password")
            create_user("other", "other-check-password")

        client = app.test_client()
        admin_token = login(client, "admin", "admin-check-password")
        author_token = login(client, "author", "author-check-password")
        other_token = login(client, "other", "other-check-password")
        admin_headers = auth_header(admin_token)
        author_headers = auth_header(author_token)
        other_headers = auth_header(other_token)

        malformed = client.post("/api/strategies", headers=author_headers, json=[])
        assert_error(malformed, 400, "json_object_required")
        invalid_name_type = client.post("/api/strategies", headers=author_headers, json={"name": 123})
        assert_error(invalid_name_type, 400, "invalid_name_type")
        long_name = client.post("/api/strategies", headers=author_headers, json={"name": "x" * 121})
        assert_error(long_name, 400, "name_too_long")

        created = client.post(
            "/api/strategies",
            headers=author_headers,
            json={"name": "安全检查策略", "strategy_type": "trend", "freq": "daily"},
        )
        assert created.status_code == 201, created.get_json()
        strategy_id = created.get_json()["strategy"]["id"]

        denied_edit = client.patch(
            f"/api/strategies/{strategy_id}",
            headers=other_headers,
            json={"name": "越权修改"},
        )
        assert_error(denied_edit, 403, "strategy_edit_denied")
        denied_version = client.post(
            f"/api/strategies/{strategy_id}/versions",
            headers=other_headers,
            json={"code": valid_code()},
        )
        assert_error(denied_version, 403, "strategy_version_denied")
        denied_delete = client.delete(f"/api/strategies/{strategy_id}", headers=other_headers)
        assert_error(denied_delete, 403, "strategy_delete_denied")

        forged_status = client.patch(
            f"/api/strategies/{strategy_id}",
            headers=author_headers,
            json={"status": "validated"},
        )
        assert_error(forged_status, 403, "strategy_status_transition_denied")
        missing_version_status = client.patch(
            f"/api/strategies/{strategy_id}",
            headers=admin_headers,
            json={"status": "ready"},
        )
        assert_error(missing_version_status, 409, "strategy_valid_version_required")
        blocked_code = client.post(
            f"/api/strategies/{strategy_id}/versions",
            headers=author_headers,
            json={
                "version_name": "blocked-import",
                "code": f"import os\n\n{valid_code()}",
            },
        )
        assert blocked_code.status_code == 201, blocked_code.get_json()
        assert blocked_code.get_json()["version"]["validation_status"] == "invalid"
        assert "高风险模块" in blocked_code.get_json()["version"]["validation_message"]

        version = client.post(
            f"/api/strategies/{strategy_id}/versions",
            headers=author_headers,
            json={"version_name": "safe-v1", "code": valid_code()},
        )
        assert version.status_code == 201, version.get_json()
        version_id = version.get_json()["version"]["id"]
        admin_status = client.patch(
            f"/api/strategies/{strategy_id}",
            headers=admin_headers,
            json={"status": "validated"},
        )
        assert admin_status.status_code == 200, admin_status.get_json()
        denied_status_downgrade = client.patch(
            f"/api/strategies/{strategy_id}",
            headers=author_headers,
            json={"status": "draft"},
        )
        assert_error(denied_status_downgrade, 403, "system_managed_strategy_read_only")
        denied_validated_version = client.post(
            f"/api/strategies/{strategy_id}/versions",
            headers=author_headers,
            json={"version_name": "validated-bypass", "code": valid_code()},
        )
        assert_error(denied_validated_version, 403, "system_managed_strategy_read_only")
        admin_draft = client.patch(
            f"/api/strategies/{strategy_id}",
            headers=admin_headers,
            json={"status": "draft"},
        )
        assert admin_draft.status_code == 200, admin_draft.get_json()
        duplicate = client.post(
            f"/api/strategies/{strategy_id}/versions",
            headers=author_headers,
            json={"version_name": "safe-v1", "code": valid_code()},
        )
        assert_error(duplicate, 409, "strategy_version_name_exists")

        detail = client.get(f"/api/strategies/{strategy_id}", headers=author_headers)
        assert detail.status_code == 200, detail.get_json()
        assert detail.headers["Cache-Control"] == "no-store"
        assert detail.headers["X-Content-Type-Options"] == "nosniff"
        assert detail.get_json()["latest_version"]["code"]
        assert all("code" not in item for item in detail.get_json()["versions"])
        version_detail = client.get(f"/api/strategy-versions/{version_id}", headers=author_headers)
        assert version_detail.status_code == 200, version_detail.get_json()
        assert version_detail.get_json()["version"]["code"] == valid_code()

        discarded = client.patch(
            f"/api/strategies/{strategy_id}",
            headers=author_headers,
            json={"status": "discarded"},
        )
        assert discarded.status_code == 200, discarded.get_json()
        discarded_version = client.post(
            f"/api/strategies/{strategy_id}/versions",
            headers=author_headers,
            json={"code": valid_code()},
        )
        assert_error(discarded_version, 409, "discarded_strategy_read_only")
        restored = client.patch(
            f"/api/strategies/{strategy_id}",
            headers=author_headers,
            json={"status": "draft"},
        )
        assert restored.status_code == 200, restored.get_json()

        with app.app_context():
            db = get_db()
            author_id = db.execute("SELECT id FROM users WHERE username='author'").fetchone()["id"]
            instrument_id = db.execute(
                """
                INSERT INTO instruments (ts_code, name, asset_type, status, is_published)
                VALUES ('000001.SZ', '平安银行', 'stock', 'ready', 1)
                """
            ).lastrowid
            db.execute(
                """
                INSERT INTO backtest_runs
                (strategy_id, strategy_version_id, instrument_id, start_date, end_date, created_by)
                VALUES (?, ?, ?, '2025-01-01', '2025-12-31', ?)
                """,
                (strategy_id, version_id, instrument_id, author_id),
            )
            db.commit()

        protected_version = client.delete(
            f"/api/strategies/{strategy_id}/versions/{version_id}",
            headers=author_headers,
        )
        assert_error(protected_version, 409, "strategy_version_in_use")
        protected_strategy = client.delete(f"/api/strategies/{strategy_id}", headers=author_headers)
        assert_error(protected_strategy, 409, "strategy_has_backtest_history")

        removable = client.post(
            "/api/strategies",
            headers=author_headers,
            json={"name": "可删除策略"},
        )
        removable_id = removable.get_json()["strategy"]["id"]
        removed = client.delete(f"/api/strategies/{removable_id}", headers=author_headers)
        assert removed.status_code == 200, removed.get_json()

    print("Quant Lab strategy security check passed.")


if __name__ == "__main__":
    main()
