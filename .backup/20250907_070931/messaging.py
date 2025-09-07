# app/integrations/messaging.py
import os
from fastapi import APIRouter, HTTPException, Query, Request
from dotenv import load_dotenv
from twilio.rest import Client

# Cargar .env una sola vez (en local). En hosting usa env del servicio.
load_dotenv(override=True)

# --- Config Twilio GLOBAL (no por request) ---
_SID   = os.getenv("TWILIO_ACCOUNT_SID")
_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
_FROM  = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

if not _SID or not _TOKEN or not _FROM:
    raise RuntimeError("Faltan credenciales TWILIO_ (SID/TOKEN/FROM)")

CLIENT = Client(_SID, _TOKEN)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.get("/debug")
def debug():
    return {"sid_ok": bool(_SID), "token_ok": bool(_TOKEN), "from": _FROM}


@router.post("/send")
def send_whatsapp(
    to:   str = Query(..., description="whatsapp:+569XXXXXXXX"),
    body: str = Query(..., description="Texto del mensaje"),
):
    try:
        msg = CLIENT.messages.create(
            from_=_FROM,
            to=to,
            body=body,
            # Callback para saber estados del mensaje enviado por /send
            status_callback=os.getenv(
                "WHATSAPP_STATUS_CALLBACK",
                "https://p01--ameth-api--c58xfw9mygtn.code.run/whatsapp/status",
            ),
        )
        return {"ok": True, "sid": msg.sid}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    """
    Webhook de recepción (Twilio envía form-url-encoded).
    Responde con confirmación y acepta JSON para tests.
    """
    from_ = None
    body  = None

    # 1) Form (Twilio)
    try:
        form = await request.form()
        from_ = form.get("From")
        body  = form.get("Body")
    except Exception:
        pass

    # 2) JSON (tests)
    if not from_ or not body:
        try:
            data = await request.json()
            from_ = from_ or data.get("From")
            body  = body  or data.get("Body")
        except Exception:
            pass

    if not from_ or not body:
        return {"ok": False, "error": "Payload inválido: se requiere From y Body"}

    print(f"📩 Entrante de {from_}: {body}")

    try:
        reply = CLIENT.messages.create(
            from_=_FROM,
            to=from_,
            body="✅ Recibido, gracias por tu mensaje. —Ameth",
            # Callback para medir latencia real del mensaje de respuesta
            status_callback=os.getenv(
                "WHATSAPP_STATUS_CALLBACK",
                "https://p01--ameth-api--c58xfw9mygtn.code.run/whatsapp/status",
            ),
        )
        return {"ok": True, "sid": reply.sid}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/status")
async def whatsapp_status(request: Request):
    """
    Twilio llamará aquí en cada cambio de estado del mensaje:
    'queued' | 'sent' | 'delivered' | 'undelivered' | 'failed', etc.
    Útil para medir latencia real sin hacer polling manual.
    """
    data = await request.form()
    # Campos típicos: MessageSid, MessageStatus, To, From, ErrorCode, ErrorMessage
    print(
        "📡 STATUS",
        data.get("MessageSid"),
        "→",
        data.get("MessageStatus"),
        "| to:", data.get("To"),
        "| err:", data.get("ErrorCode"),
    )
    # Devuelve 200 para confirmar la recepción
    return "OK"
