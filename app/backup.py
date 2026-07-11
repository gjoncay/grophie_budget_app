"""Real financial data on one laptop is a single point of failure. This
doesn't solve that (the user still needs to copy backups/ off-device
periodically) but it keeps a 30-day rolling window of local snapshots so
a bad sync or a fat-fingered edit isn't permanently destructive.
"""
import shutil
from datetime import UTC, datetime, timedelta

from app import config

RETENTION_DAYS = 30


def backup_database() -> str | None:
    if not config.DATABASE_PATH.exists():
        return None
    config.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    dest = config.BACKUPS_DIR / f"budget-{timestamp}.db"
    shutil.copy2(config.DATABASE_PATH, dest)
    _cleanup_old_backups()
    return str(dest)


def _cleanup_old_backups() -> None:
    cutoff = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)
    for backup_file in config.BACKUPS_DIR.glob("budget-*.db"):
        modified = datetime.fromtimestamp(backup_file.stat().st_mtime, tz=UTC)
        if modified < cutoff:
            backup_file.unlink()


def list_backups() -> list[dict]:
    if not config.BACKUPS_DIR.exists():
        return []
    backups = sorted(
        config.BACKUPS_DIR.glob("budget-*.db"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    return [
        {
            "filename": b.name,
            "created_at": datetime.fromtimestamp(b.stat().st_mtime, tz=UTC).isoformat(),
            "size_bytes": b.stat().st_size,
        }
        for b in backups
    ]
