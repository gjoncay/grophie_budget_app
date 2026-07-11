from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import config

app = FastAPI(title="Hearth")


@app.get("/api/health")
def health():
    return {"status": "ok"}


# In production the frontend is built to frontend/dist and served from the
# same process/port as the API. In dev, Vite's dev server proxies /api here
# instead, so this mount simply won't exist yet — that's expected.
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


def run():
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=config.PORT, reload=True)


if __name__ == "__main__":
    run()
