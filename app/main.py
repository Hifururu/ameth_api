# ameth_api/app/main.py
from __future__ import annotations
import os
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

# Routers (asegúrate de tener app/routers/__init__.py y finance.py)
from app.routers.finance import router as finance_router

def verify_api_key(request: Request):
    """
    Valida la API key simple por header 'x-api-key'.
    - Env: API_KEY (default: 'prod-xyz')
    - Para desactivar auth globalmente: export API_KEY=""
    """
    expected = os.getenv("API_KEY", "prod-xyz")
    provided = request.headers.get("x-api-key")
    if expected and provided != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")

# Identificador de build (útil para ver despliegues)
BUILD = os.getenv("BUILD", "ameth-2025-09-08-v2")

app = FastAPI(
    title="Ameth API",
    version="v1",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ?? NUEVO: importa y monta el router de Mercado Pago bajo /mp
from app.integrations.mercadopago import router as mp_router
app.include_router(mp_router, prefix="/mp", tags=["mercado_pago"])
# ?? NUEVO

# CORS (ajusta allow_origins si quieres restringir a tu dominio)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Endpoints públicos (sin API key) ----
@app.get("/health")
def health():
    return {"status": "ok", "service": "ameth", "version": "v1", "build": BUILD}

@app.get("/")
def root():
    return {"status": "ok", "message": "Welcome to Ameth API", "build": BUILD}

@app.get("/version")
def version():
    return {"build": BUILD}

# ---- Routers protegidos por API Key ----
# Aplica verify_api_key a TODO el router /finance (record, list, summary, delete, restore)
app.include_router(finance_router, dependencies=[Depends(verify_api_key)])

