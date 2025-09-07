# app/routers/messaging.py
from fastapi import APIRouter, Query
from typing import Optional
from app.integrations.telegram import send_message

router = APIRouter(prefix="/messaging", tags=["messaging"])

@router.get("/health", summary="Messaging Health", description="Simple healthcheck para el namespace /messaging.")
def messaging_health():
    return {"ok": True, "service": "messaging"}

# --- WhatsApp (placeholder para verificar webhook de Meta) ---
@router.get(
    "/whatsapp/webhook",
    summary="Whatsapp Verify",
    description="Verificación del webhook (Meta envía un GET con hub.*). Devuelve el 'challenge' si el token coincide."
)
def whatsapp_verify(
    mode: Optional[str] = None,
    challenge: Optional[str] = None,
    verify_token: Optional[str] = None,
    hub_mode: Optional[str] = None,
    hub_challenge: Optional[str] = None,
    hub_verify_token: Optional[str] = None,
):
    token = verify_token or hub_verify_token
    # Cambia "CHANGE_ME_TOKEN" por el token que configures en Meta
    if token and token == "CHANGE_ME_TOKEN":
        return challenge or hub_challenge or "ok"
    return "ok"

@router.post(
    "/whatsapp/webhook",
    summary="Whatsapp Webhook",
    description="Recepción de eventos de WhatsApp Cloud API (placeholder)."
)
def whatsapp_webhook():
    return {"ok": True}

# --- Telegram ---
@router.post(
    "/telegram/test",
    summary="Telegram Test",
    description="Envía un mensaje fijo a tu chat para verificar conectividad. Requiere TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID."
)
def telegram_test():
    res = send_message("Hola Felipe 👋, Ameth ya está conectado a Telegram ✅")
    return {"ok": True, "telegram": res.get("ok", False), "result": res.get("result")}

@router.post(
    "/telegram/send",
    summary="Telegram Send",
    description="Envía un mensaje personalizado a tu chat de Telegram. Uso: POST /messaging/telegram/send?text=Hola%20mundo"
)
def telegram_send(text: str = Query(..., description="Texto del mensaje a enviar a tu Telegram")):
    res = send_message(text)
    return {"ok": True, "telegram": res.get("ok", False), "result": res.get("result")}
