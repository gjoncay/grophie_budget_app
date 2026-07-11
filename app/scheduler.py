"""Daily sync/snapshot/backup job. Runs in-process via APScheduler so no
separate cron daemon is needed — see the plan's "Running It Locally".
"""
from apscheduler.schedulers.background import BackgroundScheduler

from app import backup, investments, networth, plaid_client, sync
from app.db import SessionLocal
from app.models import PlaidItem

_scheduler: BackgroundScheduler | None = None


def run_daily_sync() -> None:
    with SessionLocal() as db:
        for item in db.query(PlaidItem).all():
            try:
                sync.sync_item_transactions(db, item)
                investments.sync_item_investments(db, item)
            except plaid_client.PlaidNotConfigured:
                continue
        networth.recompute_net_worth_history(db)
    backup.backup_database()


def start() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(run_daily_sync, "cron", hour=6, id="daily_sync", replace_existing=True)
    _scheduler.start()
    return _scheduler


def stop() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
