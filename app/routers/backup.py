from fastapi import APIRouter

from app import backup

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.get("/status")
def status():
    backups = backup.list_backups()
    return {"backups": backups, "last_backup_at": backups[0]["created_at"] if backups else None}


@router.post("/run")
def run():
    path = backup.backup_database()
    return {"ok": path is not None, "path": path}
