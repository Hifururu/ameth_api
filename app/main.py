from __future__ import annotations

import os
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

# Routers
from app.routers.finance import router as finance_router


def verify_api_key(request: Request):
    """
    Valida la API key simple por header 'x-api-key'.
    Por defecto usa API_KEY=prod-xyz si no hay env var.
    """
    expected = os.getenv("API_KEY", "prod-xyz")
    provided = request.headers.get("x-api-key")
    if not expected:  # si quieres desactivar auth, deja API_KEY=""
        return
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")


app = FastAPI(
    title="Ameth API",
    version="v1",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS (ajusta origins si quieres restringir)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # cámbialo a tus dominios si prefieres
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- Health & root --------
@app.get("/health")
def health():
    return {"status": "ok", "service": "ameth", "version": "v1"}


@app.get("/")
def root():
    return {"status": "ok", "message": "Welcome to Ameth API"}


# -------- Routers protegidos por API Key --------
# Aplica el guard a TODO el router de finance
app.include_router(finance_router, dependencies=[Depends(verify_api_key)])

# (Ejemplo) Si luego agregas más routers:
# from app.routers.messaging import router as messaging_router
# app.include_router(messaging_router, dependencies=[Depends(verify_api_key)])
