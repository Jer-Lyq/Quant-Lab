from pathlib import Path
import os
import shutil
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def require_file(path):
    if not path.exists():
        raise AssertionError(f"missing required file: {path.relative_to(ROOT)}")


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def main():
    for relative in [
        "docker-compose.yml",
        ".env.example",
        "nginx/quant-lab.conf",
        "backend/Dockerfile",
        "backend/Dockerfile.worker",
        "backend/backtest_runtime/Dockerfile",
        "backend/requirements.txt",
        "frontend/Dockerfile",
        "frontend/package.json",
        "deploy/server-setup.md",
    ]:
        require_file(ROOT / relative)

    sys.path.insert(0, str(BACKEND))
    check_data_dir = Path(
        os.getenv(
            "QUANT_LAB_CHECK_DATA_DIR",
            str(Path(tempfile.gettempdir()) / "quant_lab_check_data"),
        )
    ).resolve()
    if check_data_dir.exists():
        shutil.rmtree(check_data_dir)
    db_path = check_data_dir / "quant_lab_check.sqlite3"

    os.environ["DATA_DIR"] = str(check_data_dir)
    os.environ["DATABASE_PATH"] = str(db_path)
    os.environ["INSTRUMENT_DATA_DIR"] = str(check_data_dir / "instruments")
    os.environ["BACKTEST_DATA_DIR"] = str(check_data_dir / "backtests")
    os.environ["BACKTEST_RUNNER"] = "dev"
    os.environ["SECRET_KEY"] = "local-check-secret"
    os.environ["ADMIN_USERNAME"] = "admin"
    os.environ["ADMIN_PASSWORD"] = "admin123456"

    from app import create_app
    from app.db import get_db, init_db
    from app.services.auth_service import create_admin_from_env
    from app.services.dataset_store import replace_ohlcv_bars
    from app.workers.backtest_worker import process_once

    app = create_app()
    with app.app_context():
        init_db()
        create_admin_from_env()
        db = get_db()
        cursor = db.execute(
            """
            INSERT INTO instruments
            (ts_code, name, asset_type, market, status, is_published, data_start, data_end)
            VALUES ('000001.SZ', '平安银行', 'stock', '主板', 'active', 1, '2024-01-02', '2024-01-12')
            """
        )
        instrument_id = cursor.lastrowid
        db.commit()
        instrument = dict(db.execute("SELECT * FROM instruments WHERE id=?", (instrument_id,)).fetchone())
        bars = []
        trade_dates = [
            "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08",
            "2024-01-09", "2024-01-10", "2024-01-11", "2024-01-12",
        ]
        for index, trade_date in enumerate(trade_dates):
            close = 10 + index * 0.12
            bars.append(
                {
                    "trade_date": trade_date,
                    "open": close - 0.05,
                    "high": close + 0.1,
                    "low": close - 0.1,
                    "close": close,
                    "volume": 1_000_000 + index * 10_000,
                    "amount": 10_000_000 + index * 100_000,
                    "adj_factor": 1.0 + index * 0.001,
                }
            )
        replace_ohlcv_bars(instrument, {"daily": bars, "weekly": []}, source="local-check")

    client = app.test_client()
    assert client.get("/api/health").status_code == 200
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    assert login.status_code == 200, login.json
    token = login.json["token"]
    headers = auth_headers(token)

    instruments = client.get("/api/instruments", headers=headers)
    assert instruments.status_code == 200, instruments.json

    strategy = client.post(
        "/api/strategies",
        headers=headers,
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

    version = client.post(
        f"/api/strategies/{strategy_id}/versions",
        headers=headers,
        json={
            "version_name": "v1-check",
            "code": "def init(context):\n    pass\n\n\ndef handle_bar(context, bar_dict):\n    pass\n",
            "notes": "结构校验应该通过",
        },
    )
    assert version.status_code == 201, version.json
    assert version.json["version"]["validation_status"] == "valid", version.json
    version_id = version.json["version"]["id"]

    disposable_version = client.post(
        f"/api/strategies/{strategy_id}/versions",
        headers=headers,
        json={
            "version_name": "v2-disposable",
            "code": "def init(context):\n    pass\n\n\ndef handle_bar(context, bar_dict):\n    pass\n",
            "notes": "用于验证未引用版本可删除",
        },
    )
    assert disposable_version.status_code == 201, disposable_version.json
    deleted_version = client.delete(
        f"/api/strategies/{strategy_id}/versions/{disposable_version.json['version']['id']}",
        headers=headers,
    )
    assert deleted_version.status_code == 200, deleted_version.json

    linked = client.post(
        f"/api/strategies/{strategy_id}/instruments",
        headers=headers,
        json={"instrument_id": instrument_id},
    )
    assert linked.status_code == 200, linked.json
    options = client.get(f"/api/backtests/options?strategy_id={strategy_id}", headers=headers)
    assert options.status_code == 200, options.json
    assert options.json["instruments"][0]["has_adjustment_factor"] is True

    created_run = client.post(
        "/api/backtests",
        headers=headers,
        json={
            "strategy_id": strategy_id,
            "strategy_version_id": version_id,
            "instrument_id": instrument_id,
            "start_date": "2024-01-02",
            "end_date": "2024-01-12",
            "initial_cash": 1_000_000,
            "commission_rate": 0.0003,
            "slippage_rate": 0.0001,
            "adjustment_mode": "qfq",
        },
    )
    assert created_run.status_code == 202, created_run.json
    run_id = created_run.json["backtest"]["id"]
    assert process_once(app, "local-check-worker") is True

    completed_run = client.get(f"/api/backtests/{run_id}", headers=headers)
    assert completed_run.status_code == 200, completed_run.json
    assert completed_run.json["backtest"]["status"] == "success", completed_run.json
    assert completed_run.json["backtest"]["dataset_hash"], completed_run.json
    assert completed_run.json["backtest"]["engine_name"] == "development-fixture", completed_run.json

    artifacts = client.get(f"/api/backtests/{run_id}/artifacts", headers=headers)
    assert artifacts.status_code == 200, artifacts.json
    assert artifacts.json["artifacts"]["equity_curve"], artifacts.json
    assert artifacts.json["artifacts"]["summary"]["trade_count"] == 1, artifacts.json

    protected_version = client.delete(
        f"/api/strategies/{strategy_id}/versions/{version_id}",
        headers=headers,
    )
    assert protected_version.status_code == 409, protected_version.json
    print("Quant Lab local and backtest checks passed.")


if __name__ == "__main__":
    main()
