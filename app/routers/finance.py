# app/routers/finance.py
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, conint

from app.storage.db import insert_record, list_records, summary_month
from app.services.notifications import notify_finance_event

router = APIRouter(prefix="/finance", tags=["finance"])

class FinanceRecord(BaseModel):
    fecha: str                 # "YYYY-MM-DD"
    concepto: str
    categoria: str
    monto_clp: conint(ge=0)
    tipo: str = Field(pattern="^(gasto|ingreso)$")

@router.post("/record")
def record_item(item: FinanceRecord):
    try:
        payload = item.model_dump()
        payload["ts"] = datetime.now(timezone.utc).isoformat()
        insert_record(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar: {e}")

    # Notificar (silencioso si falla)
    notify_finance_event(item.tipo, item.concepto, item.monto_clp, item.categoria)
    return {"ok": True}

@router.get("/list")
def list_items():
    try:
        items = list_records()
        return {"items": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar: {e}")

@router.get("/summary")
def summary(month: str):
    try:
        return summary_month(month)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en summary: {e}")
