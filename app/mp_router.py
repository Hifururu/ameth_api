import os, httpx
from fastapi import APIRouter, Request, Header
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/mp", tags=["mercadopago"])

MP_BASE = "https://api.mercadopago.com"
ACCESS_TOKEN = os.environ["MP_ACCESS_TOKEN"]
WEBHOOK_SECRET = os.environ["MP_WEBHOOK_SECRET"]
BASE_URL = os.environ.get("BASE_URL", "")

@router.post("/create_preference")
async def create_preference(title: str, quantity: int = 1, unit_price: int = 10000):
    payload = {
        "items": [{"title": title, "quantity": quantity, "unit_price": unit_price}],
        "back_urls": {
            "success": f"{BASE_URL}/mp/thanks?status=success",
            "failure": f"{BASE_URL}/mp/thanks?status=failure",
            "pending": f"{BASE_URL}/mp/thanks?status=pending",
        },
        "notification_url": f"{BASE_URL}/mp/webhook"
    }
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{MP_BASE}/checkout/preferences", json=payload, headers=headers)
    r.raise_for_status()
    data = r.json()
    return {"init_point": data.get("init_point"), "preference_id": data.get("id")}

@router.post("/webhook")
async def mp_webhook(request: Request, x_mp_secret: str | None = Header(None)):
    if x_mp_secret != WEBHOOK_SECRET:
        return {"ok": True}

    body = {}
    try:
        body = await request.json()
    except:
        pass

    payment_id = None
    if isinstance(body, dict) and "data" in body and isinstance(body["data"], dict) and "id" in body["data"]:
        payment_id = body["data"]["id"]

    if not payment_id:
        qs = dict(request.query_params)
        if qs.get("topic") == "payment" and "id" in qs:
            payment_id = qs["id"]

    if not payment_id:
        return {"ok": True}

    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{MP_BASE}/v1/payments/{payment_id}", headers=headers)
    r.raise_for_status()
    pay = r.json()

    status = pay.get("status")
    amount = pay.get("transaction_amount")
    description = pay.get("description") or "Pago Mercado Pago"
    payer_email = (pay.get("payer") or {}).get("email")
    date_created = pay.get("date_created")

    # Aquí llamarías a Kyaru para registrar el ingreso
    # kyaru.record_income(...)

    return {"processed": True, "status": status, "amount": amount, "payer": payer_email}

@router.get("/search")
async def mp_search(q: str | None = None):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    params = {"sort": "date_created", "criteria": "desc"}
    if q:
        params["q"] = q
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{MP_BASE}/v1/payments/search", headers=headers, params=params)
    r.raise_for_status()
    return r.json()
