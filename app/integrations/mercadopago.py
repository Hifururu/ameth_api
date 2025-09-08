import os, hmac, hashlib, json, httpx
from fastapi import APIRouter, Request, HTTPException
router = APIRouter()

MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
MP_WEBHOOK_SECRET = os.getenv("MP_WEBHOOK_SECRET", "")
AMETH_INTERNAL_URL = os.getenv("AMETH_INTERNAL_URL", "http://127.0.0.1:8000")
KYARU_RECORD_ENDPOINT = os.getenv("KYARU_RECORD_ENDPOINT", "/recordFinance")

def verify_mp_signature(x_signature: str, x_request_id: str, body: bytes) -> bool:
    try:
        parts = dict(p.split("=", 1) for p in (x_signature or "").split(","))
        ts, v1 = parts.get("ts"), parts.get("v1")
        if not (ts and v1 and x_request_id):
            return False
        data_id = str(json.loads(body.decode("utf-8")).get("data", {}).get("id", ""))
        manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts}"
        digest = hmac.new(MP_WEBHOOK_SECRET.encode(), manifest.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, v1)
    except Exception:
        return False

async def kyaru_post_movimiento(mov: dict) -> None:
    url = f"{AMETH_INTERNAL_URL.rstrip('/')}{KYARU_RECORD_ENDPOINT}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json=mov)
        r.raise_for_status()

@router.get("/ping")
async def mp_ping():
    return {"ok": True}

@router.post("/webhooks/mercadopago")
async def mercadopago_webhook(request: Request):
    raw = await request.body()
    x_sig = request.headers.get("x-signature")
    x_req = request.headers.get("x-request-id")
    if not (x_sig and x_req) or not verify_mp_signature(x_sig, x_req, raw):
        raise HTTPException(status_code=400, detail="invalid signature")
    print("SIG:", x_signature)
    print("REQ:", x_request_id)
    print("BODY:", raw.decode("utf-8"))


    payload = json.loads(raw.decode("utf-8"))
    payment_id = payload.get("data", {}).get("id")
    if not payment_id:
        return {"ok": True}

    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    async with httpx.AsyncClient(timeout=30) as client:
        rp = await client.get(f"https://api.mercadopago.com/v1/payments/{payment_id}", headers=headers)
        rp.raise_for_status()
        p = rp.json()

    status = p.get("status")
    amount = p.get("transaction_amount") or 0
    net = p.get("transaction_details", {}).get("net_received_amount", amount)
    desc = p.get("description") or p.get("statement_descriptor") or "Mercado Pago"
    date = p.get("date_approved") or p.get("date_created")
    currency = p.get("currency_id", "CLP")

    collector = p.get("collector_id")
    payer = p.get("payer", {}).get("id")
    tipo = "ingreso" if collector and str(collector) != str(payer) and status == "approved" else "gasto"
    if status in ["refunded", "charged_back", "cancelled", "canceled"]:
        tipo = "ajuste"

    mov = {
        "fecha": date,
        "concepto": desc,
        "monto_clp": round(float(net)),
        "monto_bruto": round(float(amount)),
        "comision": 0,
        "moneda": currency,
        "origen": "mercado_pago",
        "referencia": str(payment_id),
        "estado": status,
        "tipo": tipo,
    }
    await kyaru_post_movimiento(mov)
    return {"ok": True}

