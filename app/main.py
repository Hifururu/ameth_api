# app/main.py
from __future__ import annotations

import os
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Carga variables del .env (en local); en Northflank vendrán del panel
load_dotenv(override=True)

# Importa el router de WhatsApp ya creado en app/integrations/messaging.py
#   - Debe exponer "router = APIRouter(...)" y el endpoint POST /send
from app.integrations.messaging import router as whatsapp_router


def _origins_from_env() -> List[str]:
    # Permite configurar CORS con una lista separada por comas
    raw = os.getenv("CORS_ORIGINS", "")
    items = [x.strip() for x in raw.split(",") if x.strip()]
    return items or ["*"]  # por defecto permitir todo (útil para pruebas)


app = FastAPI(
    title="Ameth",
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
# Queda:
#   POST /whatsapp/send?to=whatsapp:+56XXXXXXXXX&body=Hola
app.include_router(whatsapp_router, prefix="/whatsapp", tags=["whatsapp"])
