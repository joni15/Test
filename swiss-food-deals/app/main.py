"""Bonnes Affaires CH — agrégateur quotidien d'offres alimentaires en Suisse.

Lancement :
    uvicorn app.main:app --reload

L'agrégation tourne au démarrage si la base est vide, puis chaque jour à
06h00 (heure suisse) via APScheduler. POST /api/refresh force une mise à jour.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import BackgroundTasks, FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import aggregator, database

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"

scheduler = BackgroundScheduler(timezone="Europe/Zurich")


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    if database.get_stats()["total_deals"] == 0:
        logger.info("Base vide — première agrégation…")
        aggregator.refresh()
    scheduler.add_job(
        aggregator.refresh,
        CronTrigger(hour=6, minute=0),
        id="daily_refresh",
        replace_existing=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="Bonnes Affaires CH",
    description="Agrégateur quotidien des meilleures offres alimentaires en Suisse",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/api/deals")
def list_deals(
    retailer: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_discount: Optional[float] = Query(default=None, ge=0, le=100),
    sort: str = Query(default="discount", pattern="^(discount|price|retailer)$"),
    limit: int = Query(default=200, ge=1, le=500),
):
    """Liste les offres du jour, filtrables et triables."""
    return {
        "deals": database.query_deals(
            retailer=retailer,
            category=category,
            search=search,
            min_discount=min_discount,
            sort=sort,
            limit=limit,
        )
    }


@app.get("/api/stats")
def stats():
    """Statistiques : nombre d'offres, détaillants, catégories, dernier refresh."""
    return database.get_stats()


@app.post("/api/refresh")
def trigger_refresh(background_tasks: BackgroundTasks):
    """Force une nouvelle agrégation (asynchrone)."""
    background_tasks.add_task(aggregator.refresh)
    return {"status": "agrégation lancée"}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
