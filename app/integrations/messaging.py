# app/integrations/messaging.py
from fastapi import APIRouter, HTTPException, Request, Query
from typing import Any, Dict, Optional
import os

router = APIRouter(prefix="/messaging", tags=["messaging"])


# ---------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------
@router.get("/health")
def messaging_health():
    """
    Simple healthcheck para el namespace /messaging.
    """
    return {"status": "ok", "service": "whatsapp"}


# ---------------------------------------------------------------------
# WhatsApp (Cloud API) - opcional, queda listo por si lo activas luego
# ---------------------------------------------------------------------
@router.get("/whatsapp/webhook")
def whatsapp_verify(
    mode: Optional[str] = None,
    challenge: Optional[str] = None,
    verify_token: Optional[str] = None,
    hub_mode: Optional[str] = None,
    hub_challenge: Optional[str] = None,
    hub_verify_token: Optional[str] = None,
):
    """
    Verificación del webhook (Meta envía un GET con hub.*).
    Devuelve el 'challenge' si el token coincide.
    """
    # Meta puede enviar ?hub.mode / ?hub.verify_token / ?hub.challenge
    mode = mode or hub_mode
    challenge = challenge or hub_challenge
    verify_token = verify_token or hub_verify_token

    expected = os.getenv("VERIFY_TOKEN", "ameth-verify-123")
    if mode == "subscribe" and verify_token == expected and challenge is not None:
        # challenge a veces viene como string numérica
        try:
            # Si es puramente numérico, devolver int; si no, devolver string
            return int(challenge) if str(challenge).isdigit() else challenge
        except Exception:
            return challenge
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    """
    Recepción de eventos de WhatsApp Cloud API.
    De momento, solo registra el payload y responde ok.
    """
    try:
        body: Dict[str, Any] = await request.json()
        # Aquí podrías parsear y actuar: enviar respuesta, guardar en DB, etc.
        print("[WHATSAPP][in]", body)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"whatsapp_webhook_error: {e}")


# ---------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------
@router.post("/telegram/test")
async def telegram_test():
    """
    Envía un mensaje fijo a tu chat para verificar conectividad.
    Requiere TELEGRAM_TOKEN y TELEGRAM_CHAT_ID en variables de entorno.
    """
    try:
        from app.integrations.telegram_client import send_telegram

        token = os.getenv("TELEGRAM_TOKEN")
        chat = os.getenv("TELEGRAM_CHAT_ID")

        if not token or not chat:
            raise RuntimeError(
                f"env_missing: TELEGRAM_TOKEN={'OK' if token else 'MISSING'}, "
                f"TELEGRAM_CHAT_ID={'OK' if chat else 'MISSING'}"
            )

        resp = await send_telegram("Hola Felipe 👋, Ameth ya está conectado a Telegram ✅")
        return {"ok": True, "telegram": resp}
    except Exception as e:
        # devolvemos el detalle para depurar rápido
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/telegram/send")
async def telegram_send(
    text: str = Query(..., description="Texto del mensaje a enviar a tu Telegram"),
):
    """
    Envía un mensaje personalizado a tu chat de Telegram.
    Uso: POST /messaging/telegram/send?text=Hola%20mundo
    """
    try:
        from app.integrations.telegram_client import send_telegram

        token = os.getenv("TELEGRAM_TOKEN")
        chat = os.getenv("TELEGRAM_CHAT_ID")

        if not token or not chat:
            raise RuntimeError(
                f"env_missing: TELEGRAM_TOKEN={'OK' if token else 'MISSING'}, "
                f"TELEGRAM_CHAT_ID={'OK' if chat else 'MISSING'}"
            )

        resp = await send_telegram(text)
        return {"sent": text, "telegram": resp}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
