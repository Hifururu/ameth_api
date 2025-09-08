# app/routers/messaging.py
from fastapi import APIRouter, Depends, Query, HTTPException
from app.security.auth import api_key_auth

# Para enviar mensajes a Telegram
from app.integrations.telegram import send_message

# Protege TODO /messaging/* con API-Key
router = APIRouter(
    prefix="/messaging",
    tags=["messaging"],
    dependencies=[Depends(api_key_auth)],
)

@router.post("/telegram/test", summary="Telegram Test",
             description="Envía un mensaje fijo a tu chat para verificar conectividad. Requiere TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID.")
def telegram_test():
    text = "Hola Felipe 👋, Ameth ya está conectado a Telegram ✅"
    try:
        res = send_message(text)
        return {"ok": True, "telegram": True, "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Telegram error: {e}")

@router.post("/telegram/send", summary="Telegram Send",
             description="Envía un mensaje personalizado a tu chat de Telegram. Uso: POST /messaging/telegram/send?text=Hola%20mundo")
def telegram_send(text: str = Query(..., description="Texto del mensaje a enviar a tu Telegram")):
    try:
        res = send_message(text)
        return {"ok": True, "telegram": True, "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Telegram error: {e}")

# --- WhatsApp deshabilitado (oculto del esquema) ---
@router.get("/whatsapp/webhook", include_in_schema=False)
def whatsapp_verify(*_, **__):
    raise HTTPException(status_code=404, detail="WhatsApp deshabilitado")

@router.post("/whatsapp/webhook", include_in_schema=False)
def whatsapp_webhook():
    raise HTTPException(status_code=404, detail="WhatsApp deshabilitado")
