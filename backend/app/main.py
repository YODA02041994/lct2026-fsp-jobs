"""Карьера ФСП — API и раздача фронтенда."""
import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .config import get_settings
from .db import init_db
from .routers import auth, catalog, candidates, tests, employers, contacts, fsp

settings = get_settings()
app = FastAPI(title="Карьера ФСП — API", version="0.1.0", root_path=settings.root_path,
              description="Платформа подбора ИТ-специалистов с обратной механикой найма и подтверждённым профилем достижений ФСП.",
              docs_url="/api/docs", openapi_url="/api/openapi.json")

API = "/api/v1"
for r in (auth.router, catalog.router, candidates.router, tests.router, employers.router, contacts.router, fsp.router):
    app.include_router(r, prefix=API)


@app.on_event("startup")
def _startup():
    os.makedirs("data", exist_ok=True)
    init_db()
    from .services.testing.engine import load_all
    from .seed import ensure_catalog
    load_all()
    ensure_catalog()


@app.get("/api/health", tags=["service"])
def health():
    from .services.testing.engine import REGISTRY
    return {"status": "ok", "templates": len(REGISTRY), "demo_mode": settings.demo_mode}


front = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", settings.frontend_dir))
if os.path.isdir(front):
    app.mount("/static", StaticFiles(directory=front), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(os.path.join(front, "index.html"))
