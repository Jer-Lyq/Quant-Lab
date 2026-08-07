from datetime import datetime, timedelta, timezone

from ..db import get_db


def _utc_text(value=None):
    value = value or datetime.now(timezone.utc)
    return value.strftime("%Y-%m-%d %H:%M:%S")


def recover_stale_jobs(max_attempts):
    now = _utc_text()
    db = get_db()
    stale = db.execute(
        "SELECT * FROM backtest_jobs WHERE status='running' AND locked_until IS NOT NULL AND locked_until < ?",
        (now,),
    ).fetchall()
    with db:
        for job in stale:
            if job["attempts"] >= max_attempts:
                db.execute(
                    "UPDATE backtest_jobs SET status='failed', error_message='worker_lease_expired', updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (job["id"],),
                )
                db.execute(
                    "UPDATE backtest_runs SET status='failed', error_message='worker_lease_expired', finished_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (job["run_id"],),
                )
            else:
                db.execute(
                    "UPDATE backtest_jobs SET status='pending', locked_by=NULL, locked_until=NULL, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (job["id"],),
                )
                db.execute(
                    "UPDATE backtest_runs SET status='queued', updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (job["run_id"],),
                )


def claim_next_job(worker_id, lease_seconds):
    db = get_db()
    lease_until = _utc_text(datetime.now(timezone.utc) + timedelta(seconds=lease_seconds))
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            """
            SELECT bj.*
            FROM backtest_jobs bj
            JOIN backtest_runs br ON br.id=bj.run_id
            WHERE bj.status='pending' AND br.status='queued'
            ORDER BY bj.priority ASC, bj.created_at ASC, bj.id ASC
            LIMIT 1
            """
        ).fetchone()
        if not row:
            db.rollback()
            return None
        updated = db.execute(
            """
            UPDATE backtest_jobs
            SET status='running', attempts=attempts+1, locked_by=?, locked_until=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=? AND status='pending'
            """,
            (worker_id, lease_until, row["id"]),
        ).rowcount
        if updated != 1:
            db.rollback()
            return None
        db.execute(
            "UPDATE backtest_runs SET status='running', started_at=COALESCE(started_at, CURRENT_TIMESTAMP), updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (row["run_id"],),
        )
        db.commit()
        return dict(row)
    except Exception:
        db.rollback()
        raise


def cancel_requested(run_id):
    row = get_db().execute(
        "SELECT cancel_requested_at, status FROM backtest_runs WHERE id=?",
        (run_id,),
    ).fetchone()
    return bool(row and (row["cancel_requested_at"] or row["status"] == "cancelled"))


def finish_cancelled(run_id):
    db = get_db()
    with db:
        db.execute(
            "UPDATE backtest_runs SET status='cancelled', finished_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (run_id,),
        )
        db.execute(
            "UPDATE backtest_jobs SET status='cancelled', locked_until=NULL, updated_at=CURRENT_TIMESTAMP WHERE run_id=?",
            (run_id,),
        )
