import os, json
from datetime import datetime
from typing import Any, Dict, Optional
import httpx
from fastapi import APIRouter, Request, HTTPException

router = APIRouter()

# === Env ===
MP_ACCESS_TOKEN        = os.getenv("MP_ACCESS_TOKEN", "")
AMETH_BASE_URL         = os.getenv("AMETH_BASE_URL", "https://api.hifururu.com")
AMETH_API_KEY          = os.getenv("AMETH_API_KEY", "")
AMETH_INTERNAL_URL     = os.getenv("AMETH_INTERNAL_URL", "")
KYARU_RECORD_ENDPOINT  = os.getenv("KYARU_RECORD_ENDPOINT", "")
DEBUG_MP               = os.getenv("DEBUG_MP", "0").lower() in ("1","true","yes")

def _dbg(*a):
    if DEBUG_MP:
        try: print(*a, flush=True)
        except: pass

def _record_endpoint() -> Dict[str, str]:
    """
    Prioriza Kyaru interno; si no, /records con x-api-key.
    """
    if AMETH_INTERNAL_URL and KYARU_RECORD_ENDPOINT:
        return {
            "url": f"{AMETH_INTERNAL_URL.rstrip('/')}{KYARU_RECORD_ENDPOINT}",
            "headers": {"Content-Type": "application/json"},
        }
    return {
        "url": f"{AMETH_BASE_URL.rstrip('/')}/records",
        "headers": {"Content-Type":"application/json", "x-api-key": AMETH_API_KEY} if AMETH_API_KEY else {"Content-Type":"application/json"},
    }

async def _get_payment(mp_id: str) -> Dict[str, Any]:
    if not (mp_id and MP_ACCESS_TOKEN):
        raise HTTPException(status_code=400, detail="missing payment id or MP access token")
    url = f"https://api.mercadopago.com/v1/payments/{mp_id}"
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(url, headers=headers)
    if r.status_code >= 300:
        _dbg("MP get payment failed:", r.status_code, r.text)
        raise HTTPException(status_code=200, detail="skip")  # no reintentar
    return r.json()

def _to_record(p: Dict[str, Any]) -> Dict[str, Any]:
    fecha_raw = p.get("date_approved") or p.get("date_created") or ""
    try:
        fecha = (fecha_raw or "")[:10] or datetime.utcnow().date().isoformat()
    except:
        fecha = datetime.utcnow().date().isoformat()

    concepto: Optional[str] = p.get("description") or p.get("statement_descriptor")
    if not concepto:
        addi = p.get("additional_info") or {}
        items = addi.get("items") or []
        if isinstance(items, list) and items and items[0].get("title"):
            concepto = items[0]["title"]
    if not concepto:
        concepto = f"MercadoPago {p.get('payment_method_id', 'pago')}"

    try:
        monto_clp = int(round(float(p.get("transaction_amount") or 0)))
    except:
        monto_clp = 0

    status = (p.get("status") or "").lower()
    tipo = "ingreso" if status in {"refunded","cancelled"} else "gasto"

    return {
        "fecha": fecha,
        "concepto": concepto,
        "categoria": "otros",
        "monto_clp": monto_clp,
        "tipo": tipo,
    }

@router.get("/ping")
async def mp_ping():
    return {"ok": True}

@router.post("/webhooks/mercadopago")
async def mp_webhook(request: Request):
    """
    Versión simple: NO valida firma. Busca el pago en MP y lo guarda como RecordIn.
    """
    raw = await request.body()
    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except:
        _dbg("invalid json body")
        return {"ok": True, "skipped": True}

    if (payload.get("type") or "").lower() != "payment":
        return {"ok": True, "skipped": True}

    mp_id = ((payload.get("data") or {}) or {}).get("id")
    if not mp_id:
        _dbg("missing payment id")
        return {"ok": True, "skipped": True}

    # 1) Detalle del pago
    try:
        p = await _get_payment(str(mp_id))
    except HTTPException:
        return {"ok": True, "skipped": True}

    # 2) Mapear y guardar
    record = _to_record(p)
    conf = _record_endpoint()
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(conf["url"], headers=conf["headers"], json=record)
        if r.status_code >= 300:
            _dbg("save failed:", r.status_code, r.text)
            return {"ok": True, "stored": False}
    except Exception as e:
        _dbg("save exception:", repr(e))
        return {"ok": True, "stored": False}

    _dbg("stored:", record)
    return {"ok": True, "stored": True}
