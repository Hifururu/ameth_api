# app/integrations/mercadopago.py
import os
import json
import hmac
import hashlib
from typing import Dict, Any

import httpx
from fastapi import APIRouter, Request, HTTPException

router = APIRouter()

# ====== Env Vars ======
MP_ACCESS_TOKEN: str = os.getenv("MP_ACCESS_TOKEN", "")
MP_WEBHOOK_SECRET: str = os.getenv("MP_WEBHOOK_SECRET", "")
AMETH_INTERNAL_URL: str = os.getenv("AMETH_INTERNAL_URL", "http://127.0.0.1:8000")
KYARU_RECORD_ENDPOINT: str = os.getenv("KYARU_RECORD_ENDPOINT", "/recordFinance")
DEBUG_MP: bool = os.getenv("DEBUG_MP", "0").lower() in ("1", "true", "yes")

# ====== Utils ======
def _debug(*args):
    if DEBUG_MP:
        try:
            print(*args, flush=True)
        except Exception:
            pass

def parse_signature(sig_header: str) -> Dict[str, str]:
    """
    x-signature típico: 'ts=<unix>, v1=<hex>' (puede traer espacios).
    Devuelve {'ts': '...', 'v1': '...'} o {}.
    """
    parts: Dict[str, str] = {}
    if not sig_header:
        return parts
    for piece in sig_header.split(","):
        if "=" in piece:
            k, v = piece.split("=", 1)
            parts[k.strip().lower()] = v.strip()
    return parts

def verify_mp_signature(x_signature: str, x_request_id: str, body: bytes) -> bool:
    """
    Manifest: 'id:<data.id>;request-id:<x-request-id>;ts:<ts>'
    HMAC-SHA256 usando MP_WEBHOOK_SECRET. Compara con 'v1'.
    """
    try:
        if not (x_signature and x_request_id and body):
            return False

        sig = parse_signature(x_signature)
        ts = sig.get("ts")
        v1 = sig.get("v1")
        if not (ts and v1):
            return False

        data = json.loads(body.decode("utf-8") or "{}")
        data_id = str(((data or {}).get("data") or {}).get("id") or "")

        manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts}"
        digest = hmac.new(MP_WEBHOOK_SECRET.encode(), manifest.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, v1)
    except Exception as e:
        _debug("verify_mp_signature error:", repr(e))
        return False

async def kyaru_post_movimiento(mov: Dict[str, Any]) -> None:
    url = f"{AMETH_INTERNAL_URL.rstrip('/')}{KYARU_RECORD_ENDPOINT}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json=mov)
        r.raise_for_status()

# ====== Endpoints ======
@router.get("/ping")
async def mp_ping():
    return {"ok": True}

@router.post("/webhooks/mercadopago")
async def mercadopago_webhook(request: Request):
    raw = await request.body()
    x_sig = request.headers.get("x-signature")
    x_req = request.headers.get("x-request-id")

    # Logs de diagnóstico (activar con DEBUG_MP=1)
    _debug("SIG:", x_sig)
    _debug("REQ:", x_req)
    _debug("BODY:", raw.decode("utf-8", errors="ignore"))

    # Validación condicional de firma:
    # - si hay MP_WEBHOOK_SECRET => exigir firma válida
    # - si no hay (vacío) => omitir validación (modo prueba)
    if MP_WEBHOOK_SECRET and not verify_mp_signature(x_sig, x_req, raw):
        raise HTTPException(status_code=400, detail="invalid signature")

    # Parseo seguro del body
    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        payload = {}

    # Tolerar simulador / pruebas: live_mode:false => responder 200 sin consultar API
    if not payload or payload.get("live_mode") is False:
        _debug("Simulador o live_mode:false → 200 OK")
        return {"ok": True}

    payment_id = (payload.get("data") or {}).get("id")
    if not payment_id:
        return {"ok": True}

    # Consultar detalle del pago (tolerante a errores: si falla, igual respondemos 200)
    detalle = None
    try:
        headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"} if MP_ACCESS_TOKEN else {}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"https://api.mercadopago.com/v1/payments/{payment_id}",
                headers=headers or None,
            )
        if resp.status_code >= 400:
            _debug("MP payments API non-200:", resp.status_code, resp.text)
            return {"ok": True}  # no romper flujo por pruebas o ids ficticios
        detalle = resp.json()
    except Exception as e:
        _debug("Error consultando MP:", repr(e))
        return {"ok": True}

    # Mapear a movimiento para Kyaru y enviar (si hay detalle)
    try:
        p = detalle or {}
        status = p.get("status")
        amount = p.get("transaction_amount") or 0
        net = (p.get("transaction_details") or {}).get("net_received_amount", amount)
        desc = p.get("description") or p.get("statement_descriptor") or "Mercado Pago"
        date = p.get("date_approved") or p.get("date_created")
        currency = p.get("currency_id", "CLP")

        collector = p.get("collector_id")
        payer = (p.get("payer") or {}).get("id")
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
        _debug("MOV→Kyaru:", mov)
        await kyaru_post_movimiento(mov)
    except Exception as e:
        _debug("Error armando/enviando mov:", repr(e))
        # No interrumpir; igualmente devolver OK para evitar reintentos del simulador

    return {"ok": True}


