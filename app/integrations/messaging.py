from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
import os
from typing import Any, Dict, Optional

router = APIRouter(prefix="/messaging", tags=["messaging"])

@router.get("/health")
def messaging_health():
    return {"status": "ok", "service": "whatsapp"}

# ---------- WhatsApp (opcional, ya lo tenías) ----------
@router.get("/whatsapp/webhook")
def whatsapp_verify(mode: Optional[str] = None, challenge: Optional[str] = None, verify_token: Optional[str] = None,
                    hub_mode: Optional[str] = None, hub_challenge: Optional[str] = None, hub_verify_token: Optional[str] = None):
    mode = mode or hub_mode
    challenge = challenge or hub_challenge
    verify_token = verify_token or hub_verify_token
    EXPECTED = os.getenv("VERIFY_TOKEN", "ameth-verify-123")
    if mode == "subscribe" and verify_token == EXPECTED and challenge:
        return int(challenge) if str(challenge).isdigit() else challenge
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request, bg: BackgroundTasks):
    body = await request.json()
    def process(data: Dict[str, Any]):
        print("[WHATSAPP][in]", data)
    bg.add_task(process, body)
    return {"ok": True}

# ---------- Telegram: TEST ----------
from app.integrations.telegram_client import send_telegram

@router.post("/telegram/test")
async def telegram_test():
    import asyncio
    await send_telegram("Hola Felipe 👋, Ameth ya está conectado a Telegram ✅")
    return {"ok": True}
