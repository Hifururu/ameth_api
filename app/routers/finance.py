# app/routers/finance.py
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.security.auth import api_key_auth
from app.storage.db import record_item, list_items, month_summary

# Protege TODO /finance/* con API-Key
router = APIRouter(
    prefix="/finance",
    tags=["finance"],
    dependencies=[Depends(api_key_auth)],
)

class FinanceRecord(BaseModel):
    fecha: str = Field(..., title="Fecha")  # YYYY-MM-DD
    concepto: str = Field(..., title="Concepto")
    categoria: str = Field(..., title="Categoria")
    monto_clp: int = Field(..., ge=0, title="Monto Clp")
    tipo: str = Field(..., pattern="^(gasto|ingreso)$", title="Tipo")  # gasto|ingreso

@router.post("/record", summary="Record Item")
def record_item_endpoint(payload: FinanceRecord):
    ok = record_item(payload.model_dump())
    return {"ok": ok}

@router.get("/list", summary="List Items")
def list_items_endpoint():
    items = list_items()
    count = len(items) if isinstance(items, list) else items.get("count", 0)
    return {"items": items, "count": count}

@router.get("/summary", summary="Summary")
def summary_finance(month: str = Query(..., description="YYYY-MM")):
    return month_summary(month)
