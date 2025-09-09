# app/main.py
from __future__ import annotations

import os
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Cargar .env en local (en hosting vendrán del sistema)
load_dotenv(override=True)

# Router de WhatsApp ya tiene prefix="/whatsapp" internamente
from app.integrations.messaging import router as whatsapp_router


def _origins_from_env() -> List[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    items = [x.strip() for x in raw.split(",") if x.strip()]
    return items or ["*"]  # por defecto permitir todo para pruebas

app = FastAPI(
    title="Ameth API",
    version="v1",
    description="API base de Ameth con WhatsApp (Twilio) y healthcheck",
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins_from_env(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Rutas base ---
@app.get("/", tags=["system"])
def root():
    return {"message": "Hello from Ameth!"}

@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "ameth", "version": "v1"}

# --- Montar WhatsApp ---
# OJO: NO repetir prefix aquí, ya lo trae el router (quedaría /whatsapp/whatsapp)
app.include_router(whatsapp_router)


from app.integrations.mercadopago import router as mp_router
app.include_router(mp_router, prefix="/mp", tags=["mercado_pago"])

# === auto-include finance router ===
finance = None
try:
    # preferir import relativo (estamos dentro del paquete 'app')
    from .routers import finance as finance
except Exception as e1:
    try:
        from app.routers import finance as finance
    except Exception as e2:
        print(f"Finance router not loaded: {e1 or e2}")

if finance:
    try:
        app.include_router(finance.router, prefix="/finance", tags=["finance"])
    except Exception as e:
        print(f"Finance router include failed: {e}")
# === end auto-include ===
