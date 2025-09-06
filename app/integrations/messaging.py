# app/integrations/messaging.py
import os
from fastapi import APIRouter, HTTPException, Query, Request
from twilio.rest import Client
from dotenv import load_dotenv

# Cargar .env en local; en hosting vendrán del panel de Environment
load_dotenv(override=True)

# Router con prefijo propio (NO repetir en main.py)
router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

def _get_twilio():
    sid   = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_ = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    if not sid or not token or not from_:
        raise HTTPException(
            status_code=500,
            detail="Faltan credenciales TWILIO_ (SID/TOKEN/FROM)"
        )
    return Client(sid, token), from_

@router.get("/debug")
def debug():
    return {
        "sid_ok":   bool(os.getenv("TWILIO_ACCOUNT_SID")),
        "token_ok": bool(os.getenv("TWILIO_AUTH_TOKEN")),
        "from":     os.getenv("TWILIO_WHATSAPP_FROM"),
    }

@router.post("/send")
def send_whatsapp(
    to:   str = Query(..., description="whatsapp:+569XXXXXXXX"),
    body: str = Query(..., description="Texto del mensaje"),
):
    try:
        client, FROM = _get_twilio()
        msg = client.messages.create(from_=FROM, to=to, body=body)
        return {"ok": True, "sid": msg.sid}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    """
    Webhook de recepción (Twilio envía POST x-www-form-urlencoded).
    Responde automáticamente con un mensaje de confirmación.
    También acepta JSON para pruebas locales.
    """
    from_ = None
    body  = None

    # 1) Form (lo que envía Twilio)
    try:
        form = await request.form()
        from_ = form.get("From")
        body  = form.get("Body")
    except Exception:
        pass

    # 2) JSON (para tests)
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
        client, FROM = _get_twilio()
        reply = client.messages.create(
            from_=FROM,
            to=from_,
            body="✅ Recibido, gracias por tu mensaje. —Ameth"
        )
        return {"ok": True, "sid": reply.sid}
    except Exception as e:
        return {"ok": False, "error": str(e)}

