import os
from fastapi import FastAPI, Depends
from fastapi.openapi.utils import get_openapi
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

# Routers
from app.routers.messaging import router as messaging_router
from app.routers.finance   import router as finance_router

# Auth por API key
from app.security.auth     import api_key_auth

# Notificaciones (scheduler)
from app.services.notifications import daily_greeting_summary

load_dotenv()

app = FastAPI(title="Ameth API", version="v2.3")

# ⚠️ Importante: SOLO estos include_router (elimina cualquier include viejo sin Depends)
app.include_router(messaging_router, dependencies=[Depends(api_key_auth)])
app.include_router(finance_router,   dependencies=[Depends(api_key_auth)])

# Salud pública (sin auth)
@app.get("/health", summary="Health")
def health():
    return {"status": "ok", "service": "ameth", "version": app.version}

# --- OpenAPI con esquema de API key en header x-api-key ---
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
    # Nota: Esto solo documenta; la verificación real la hace Depends(api_key_auth).
    openapi_schema["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi  # type: ignore[assignment]

# --- Scheduler diario (07:00 America/Santiago) ---
_scheduler: BackgroundScheduler | None = None

@app.on_event("startup")
def _start_scheduler():
    global _scheduler
    if _scheduler is None:
        tz = os.getenv("TZ", "America/Santiago")
        _scheduler = BackgroundScheduler(timezone=tz)
        _scheduler.add_job(
            daily_greeting_summary,
            "cron",
            hour=7,
            minute=0,
            id="daily_summary",
            replace_existing=True,
        )
        _scheduler.start()

@app.on_event("shutdown")
def _stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
