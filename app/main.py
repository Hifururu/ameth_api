from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

from app.storage.db import init_db
from app.routers.finance import router as finance_router
from app.routers.messaging import router as messaging_router
from app.services.notifications import daily_greeting_summary

app = FastAPI(title="Ameth API", version="v2.1")  # ← sube versión para verificar deploy

# Routers
app.include_router(finance_router)     # ← IMPORTANTE
app.include_router(messaging_router)

# Scheduler (resumen diario a las 07:00 América/Santiago)
scheduler = BackgroundScheduler(timezone=ZoneInfo("America/Santiago"))

@app.on_event("startup")
def on_startup():
    init_db()  # ← crea tablas si no existen
    scheduler.add_job(
        daily_greeting_summary,
        CronTrigger(hour=7, minute=0),
        id="daily_summary_7am",
        replace_existing=True,
    )
    scheduler.start()

@app.on_event("shutdown")
def on_shutdown():
    if scheduler.running:
        scheduler.shutdown(wait=False)

@app.get("/health", summary="Health")
def health():
    return {"status": "ok", "service": "ameth", "version": "v2.0"}
