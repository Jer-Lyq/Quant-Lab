import json
import math
import os
import platform
import statistics
import subprocess
import time
from pathlib import Path

from flask import current_app


WORKER_VERSION = "quant-lab-backtest-worker/1"


class RunnerError(RuntimeError):
    def __init__(self, message, *, exit_code=None, output=None):
        super().__init__(message)
        self.exit_code = exit_code
        self.output = output


def _drawdown_curve(equity):
    peak = None
    output = []
    for item in equity:
        value = item["unit_net_value"]
        peak = value if peak is None else max(peak, value)
        output.append({"date": item["date"], "drawdown": value / peak - 1 if peak else 0})
    return output


def _summary(equity, trades):
    values = [item["unit_net_value"] for item in equity]
    returns = [values[index] / values[index - 1] - 1 for index in range(1, len(values)) if values[index - 1]]
    total_return = values[-1] - 1 if values else 0
    annual_return = (1 + total_return) ** (252 / max(len(returns), 1)) - 1 if total_return > -1 else -1
    volatility = statistics.pstdev(returns) * math.sqrt(252) if len(returns) > 1 else 0
    sharpe = statistics.mean(returns) / statistics.pstdev(returns) * math.sqrt(252) if len(returns) > 1 and statistics.pstdev(returns) else None
    drawdowns = [item["drawdown"] for item in _drawdown_curve(equity)]
    nonzero = [value for value in returns if value != 0]
    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "max_drawdown": min(drawdowns, default=0),
        "sharpe": sharpe,
        "volatility": volatility,
        "win_rate": sum(1 for value in nonzero if value > 0) / len(nonzero) if nonzero else None,
        "trade_count": len(trades),
    }


class DisabledRunner:
    def run(self, _snapshot, _cancel_check):
        raise RunnerError("backtest_runner_disabled")


class DevelopmentFixtureRunner:
    """Exercises the queue and result contract without executing user code."""

    def run(self, snapshot, cancel_check):
        bars = snapshot["snapshot"]["bars"]
        config = json.loads((snapshot["input_dir"] / "run.json").read_text(encoding="utf-8"))
        commission = float(config["commission_rate"])
        slippage = float(config["slippage_rate"])
        initial_cash = float(config["initial_cash"])
        entry_price = float(bars[0]["close"]) * (1 + slippage)
        shares = math.floor(initial_cash / (entry_price * (1 + commission)) / 100) * 100
        entry_cost = shares * entry_price
        fee = entry_cost * commission
        cash = initial_cash - entry_cost - fee
        trades = [{
            "datetime": bars[0]["trade_date"],
            "order_book_id": snapshot["snapshot"]["instrument"]["order_book_id"],
            "side": "BUY",
            "last_price": entry_price,
            "quantity": shares,
            "transaction_cost": fee,
        }] if shares else []
        equity = []
        for bar in bars:
            if cancel_check():
                raise RunnerError("backtest_cancelled")
            total_value = cash + shares * float(bar["close"])
            equity.append({
                "date": bar["trade_date"],
                "unit_net_value": total_value / initial_cash,
                "total_value": total_value,
            })
        return {
            "engine_name": "development-fixture",
            "engine_version": "1",
            "worker_version": WORKER_VERSION,
            "exit_code": 0,
            "warning": "开发模拟执行器仅验证任务、数据和展示链路，未执行策略代码。",
            "summary": _summary(equity, trades),
            "equity_curve": equity,
            "drawdown_curve": _drawdown_curve(equity),
            "trades": trades,
            "positions": [],
            "raw_output": {"runner": "development-fixture", "python": platform.python_version()},
        }


class DockerRqalphaRunner:
    def run(self, snapshot, cancel_check):
        docker = os.getenv("BACKTEST_DOCKER_COMMAND", "docker")
        bundle = Path(current_app.config["RQALPHA_BUNDLE_DIR"]).resolve()
        if not bundle.exists():
            raise RunnerError("rqalpha_bundle_missing")
        input_dir = snapshot["input_dir"].resolve()
        output_dir = snapshot["output_dir"].resolve()
        data_root = Path(current_app.config["DATA_DIR"]).resolve()
        host_data_root = current_app.config["BACKTEST_HOST_DATA_DIR"]
        if host_data_root:
            host_data_root = Path(host_data_root).resolve()
            host_input_dir = host_data_root / input_dir.relative_to(data_root)
            host_output_dir = host_data_root / output_dir.relative_to(data_root)
        else:
            host_input_dir = input_dir
            host_output_dir = output_dir
        host_bundle = Path(current_app.config["RQALPHA_HOST_BUNDLE_DIR"] or bundle).resolve()
        command = [
            docker, "run", "--rm", "--network", "none", "--read-only",
            "--cpus", "1", "--memory", "512m", "--pids-limit", "128",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=134217728",
            "-v", f"{host_input_dir}:/input:ro",
            "-v", f"{host_output_dir}:/output:rw",
            "-v", f"{host_bundle}:/bundle:ro",
            current_app.config["BACKTEST_DOCKER_IMAGE"],
        ]
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        except OSError as exc:
            raise RunnerError("docker_runner_unavailable", output=str(exc)) from exc

        deadline = time.monotonic() + current_app.config["BACKTEST_TIMEOUT_SECONDS"]
        while process.poll() is None:
            if cancel_check():
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                raise RunnerError("backtest_cancelled")
            if time.monotonic() >= deadline:
                process.kill()
                raise RunnerError("backtest_timeout")
            time.sleep(0.5)
        output = (process.stdout.read() if process.stdout else "")[-65536:]
        if process.returncode != 0:
            raise RunnerError("rqalpha_execution_failed", exit_code=process.returncode, output=output)
        result_path = output_dir / "result.json"
        if not result_path.exists():
            raise RunnerError("rqalpha_result_missing", exit_code=process.returncode, output=output)
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result.setdefault("worker_version", WORKER_VERSION)
        result.setdefault("exit_code", process.returncode)
        result.setdefault("raw_output", {"log": output})
        return result


def get_runner():
    mode = current_app.config["BACKTEST_RUNNER"]
    if mode == "dev":
        return DevelopmentFixtureRunner()
    if mode == "docker":
        return DockerRqalphaRunner()
    return DisabledRunner()
