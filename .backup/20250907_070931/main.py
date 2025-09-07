# app/main.py
from __future__ import annotations

import os
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Cargar .env en local; en hosting las lee del entorno (Northflank)
load_dotenv(override=True)

# Router de WhatsApp (ya trae prefix="/whatsapp" internamente)
from app.integrations.messaging import router as whatsapp_router


def _origins_from_env() -> List[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    items = [x.strip() for x in raw.split(",") if x.strip()]
    return items or ["*"]  # permitir todo en pruebas

app = FastAPI(
    title="Ameth API",
    version="v1",
    description="API base de Ameth con WhatsApp (Twilio), healthcheck y webhook",
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
# ¡NO repetir prefix aquí! (evita /whatsapp/whatsapp)
app.include_router(whatsapp_router)

