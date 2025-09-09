# app/integrations/messaging.py
import os
from fastapi import APIRouter, HTTPException, Query
from twilio.rest import Client
from dotenv import load_dotenv

# Cargar variables del .env (local). En hosting se usan envs del servicio.
load_dotenv(override=True)

# Router que importa app.main
router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

def _get_twilio():
    sid   = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_ = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    if not sid or not token or not from_:
        raise HTTPException(
            status_code=500,
            detail="Faltan credenciales TWILIO_ en .env (SID/TOKEN/FROM)"
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
    to:   str = Query(..., description="whatsapp:+56XXXXXXXXX"),
    body: str = Query(..., description="Texto del mensaje"),
):
    try:
        client, FROM = _get_twilio()
        msg = client.messages.create(from_=FROM, to=to, body=body)
        return {"ok": True, "sid": msg.sid}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
