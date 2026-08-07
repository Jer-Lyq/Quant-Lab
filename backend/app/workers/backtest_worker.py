import argparse
import os
import socket
import time

from .. import create_app
from ..services.backtest_queue import cancel_requested, claim_next_job, finish_cancelled, recover_stale_jobs
from ..services.backtest_runners import RunnerError, get_runner
from ..services.backtest_service import finish_backtest_failure, finish_backtest_success, get_backtest
from ..services.backtest_snapshot import build_run_snapshot


def process_once(app, worker_id):
    with app.app_context():
        recover_stale_jobs(app.config["BACKTEST_JOB_MAX_ATTEMPTS"])
        job = claim_next_job(worker_id, app.config["BACKTEST_JOB_LEASE_SECONDS"])
        if not job:
            return False
        run_id = job["run_id"]
        try:
            snapshot = build_run_snapshot(run_id)
            runner = get_runner()
            result = runner.run(snapshot, lambda: cancel_requested(run_id))
            if cancel_requested(run_id):
                finish_cancelled(run_id)
            else:
                refreshed = get_backtest(run_id)
                snapshot["run"]["dataset_snapshot_path"] = refreshed.get("dataset_snapshot_path")
                finish_backtest_success(run_id, result, snapshot)
        except RunnerError as exc:
            if str(exc) == "backtest_cancelled" or cancel_requested(run_id):
                finish_cancelled(run_id)
            else:
                finish_backtest_failure(run_id, str(exc), exc.exit_code, exc.output)
        except Exception as exc:
            app.logger.exception("Backtest worker failed for run %s", run_id)
            finish_backtest_failure(run_id, str(exc))
        return True


def main():
    parser = argparse.ArgumentParser(description="Quant Lab backtest worker")
    parser.add_argument("--once", action="store_true", help="Process at most one queued job")
    args = parser.parse_args()
    app = create_app()
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    while True:
        processed = process_once(app, worker_id)
        if args.once:
            break
        if not processed:
            time.sleep(app.config["BACKTEST_WORKER_POLL_SECONDS"])


if __name__ == "__main__":
    main()
