# app/main.py
import os
from typing import Optional
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

# Routers
from app.routers.messaging import router as messaging_router
from app.routers.finance   import router as finance_router

# Scheduler job (lo envolvemos en try por si no existe el módulo en alguna build)
try:
    from app.services.notifications import daily_greeting_summary  # type: ignore
except Exception:
    daily_greeting_summary = None  # type: ignore

load_dotenv()

app = FastAPI(title="Ameth API", version="v2.4")

# Incluye routers (ya están protegidos a nivel de router con API-Key)
app.include_router(messaging_router)
app.include_router(finance_router)

# Salud pública (sin auth)
@app.get("/health", summary="Health")
def health():
    return {"status": "ok", "service": "ameth", "version": app.version}

# OpenAPI con esquema de API-Key (documentación)
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
        description="Ameth API (Telegram + Finanzas) con API-Key.",
    )
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["ApiKeyAuth"] = {
        "type": "apiKey",
        "in": "header",
        "name": "x-api-key",
    }
    # Nota: la verificación real ya la hace cada router; esto solo es documental.
    openapi_schema["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi  # type: ignore[assignment]

# Scheduler diario (07:00 America/Santiago)
_scheduler: Optional[BackgroundScheduler] = None

@app.on_event("startup")
def _start_scheduler():
    global _scheduler
    if _scheduler is None:
        tz = os.getenv("TZ", "America/Santiago")
        _scheduler = BackgroundScheduler(timezone=tz)
        if callable(daily_greeting_summary):
            _scheduler.add_job(
                daily_greeting_summary, "cron",
                hour=7, minute=0,
                id="daily_summary", replace_existing=True
            )
        _scheduler.start()

@app.on_event("shutdown")
def _stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
