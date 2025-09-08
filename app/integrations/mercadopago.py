from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
async def mp_ping():
    return {"ok": True}

@router.post("/webhooks/mercadopago")
async def mp_webhook():
    return {"ok": True}
