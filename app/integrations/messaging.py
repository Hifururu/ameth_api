from fastapi import APIRouter, Request, BackgroundTasks

router = APIRouter(prefix="/messaging", tags=["messaging"])

@router.get("/health")
def messaging_health():
    return {"status": "ok", "service": "whatsapp"}

@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request, bg: BackgroundTasks):
    payload = await request.json()

    # Procesamiento asíncrono (TTFB rápido)
    def process_message(data: dict):
        # TODO: aquí parseas el mensaje y respondes con tu proveedor (Twilio/Cloud API)
        # Por ahora sólo imprime en logs del servidor:
        print("[WHATSAPP] payload:", data)

    bg.add_task(process_message, payload)
    return {"ok": True}
