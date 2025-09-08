from __future__ import annotations

import os
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

# Routers
from app.routers.finance import router as finance_router


def verify_api_key(request: Request):
    """
    Valida la API key simple por header 'x-api-key'.
    Si no configuras API_KEY, por defecto usa 'prod-xyz'.
    Para desactivar auth globalmente, setea API_KEY="" en env.
    """
    expected = os.getenv("API_KEY", "prod-xyz")
    provided = request.headers.get("x-api-key")
    if expected and provided != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")


# === Identificador de build para /version y /health ===
BUILD = os.getenv("BUILD", "local-dev")

app = FastAPI(
    title="Ameth API",
    version="v1",
    docs_url="/docs",
    redoc_url="/redoc",
)

# === CORS (ajusta allow_origins si quieres restringir) ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # coloca tus dominios aquí si quieres restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Endpoints públicos ===
@app.get("/health")
def health():
    return {"status": "ok", "service": "ameth", "version": "v1", "build": BUILD}

@app.get("/")
def root():
    return {"status": "ok", "message": "Welcome to Ameth API", "build": BUILD}

@app.get("/version")
def version():
    return {"build": BUILD}

# === Routers protegidos por API Key ===
# Aplica la validación 'verify_api_key' a TODO el router /finance
app.include_router(finance_router, dependencies=[Depends(verify_api_key)])
