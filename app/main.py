from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import config, scheduler
from app.routers import (
    accounts,
    backup,
    budget_targets,
    categories,
    dashboard,
    investments,
    plaid,
    spending,
    transactions,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(title="Hearth", lifespan=lifespan)
app.include_router(plaid.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(dashboard.router)
app.include_router(investments.router)
app.include_router(spending.router)
app.include_router(budget_targets.router)
app.include_router(backup.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# In production the frontend is built to frontend/dist and served from the
# same process/port as the API. In dev, Vite's dev server proxies /api here
# instead, so this mount simply won't exist yet — that's expected.
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="frontend-assets")

    # StaticFiles(html=True) alone only serves index.html for "/" — a direct
    # load or refresh on a client-side route like /accounts 404s otherwise.
    # This catch-all serves the real file if one exists on disk, else falls
    # back to index.html so React Router can take over.
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        candidate = frontend_dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(frontend_dist / "index.html")


def run():
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=config.PORT, reload=True)


if __name__ == "__main__":
    run()
