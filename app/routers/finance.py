from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Literal, Optional

from app.storage.finance_storage import (
    add_record,
    list_records,
    summary_month,
    delete_record as storage_delete_record,
    clear_month as storage_clear_month,
    dedupe_month,
    export_month,
)

router = APIRouter(prefix="/finance", tags=["finance"])


# ====== Schemas ======
class RecordIn(BaseModel):
    fecha: str = Field(..., description="YYYY-MM-DD")
    concepto: str
    categoria: str
    monto_clp: int
    tipo: Literal["gasto", "ingreso"]


# ====== Endpoints ======
@router.post("/record")
def record_item(payload: RecordIn):
    """
    Crea un registro. Con idempotencia: si existe el mismo (fecha, concepto, categoria, monto, tipo),
    devuelve el existente con created=False.
    """
    rec, created = add_record(
        fecha=payload.fecha,
        concepto=payload.concepto,
        categoria=payload.categoria,
        monto_clp=payload.monto_clp,
        tipo=payload.tipo,
        enforce_idempotency=True,
    )
    return {
        "ok": True,
        "created": created,
        "record": rec,
        "note": None if created else "Registro duplicado (idempotente): se devolvió el existente.",
    }


@router.get("/list")
def list_items(month: Optional[str] = Query(default=None, description="YYYY-MM opcional")):
    """
    Lista registros. Si 'month' (YYYY-MM) viene, filtra por mes.
    """
    items = list_records(month=month)
    return {"items": items, "count": len(items)}


@router.get("/summary")
def summary(month: str = Query(..., description="YYYY-MM")):
    """
    Resumen del mes: ingresos, gastos, saldo y cantidad de ítems.
    """
    return summary_month(month)


@router.post("/dedupe")
def dedupe(month: str = Query(..., description="YYYY-MM")):
    """
    Elimina duplicados dentro del mes basándose en la clave de idempotencia.
    Conserva el primero cronológico.
    """
    removed = dedupe_month(month)
    return {"ok": True, "month": month, "removed": removed}


@router.post("/clear")
def clear(month: str = Query(..., description="YYYY-MM")):
    """
    Borra todos los registros del mes dado.
    """
    removed = storage_clear_month(month)
    return {"ok": True, "month": month, "removed": removed}


@router.delete("/{record_id}")
def delete_record(record_id: str):
    """
    Borra un registro por su ID.
    """
    ok = storage_delete_record(record_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return {"ok": True, "deleted_id": record_id}


@router.get("/export")
def export(
    month: str = Query(..., description="YYYY-MM"),
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
):
    """
    Exporta registros del mes a CSV (siempre disponible) o XLSX (requiere openpyxl).
    """
    try:
        data, mime, filename = export_month(month, format)
    except RuntimeError as e:
        # Ej.: falta 'openpyxl' para XLSX
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return StreamingResponse(
        iter([data]),
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
from fastapi import Body
from pydantic import BaseModel, Field
from typing import Optional, Literal
from app.storage.finance_storage import _load_db, _save_db, ensure_schema, list_records

@router.get("/{record_id}")
def get_record(record_id: str):
    for r in list_records():
        if r.get("id") == record_id:
            return r
    raise HTTPException(status_code=404, detail="Registro no encontrado")

class RecordUpdate(BaseModel):
    fecha: Optional[str] = Field(None, description="YYYY-MM-DD")
    concepto: Optional[str] = None
    categoria: Optional[str] = None
    monto_clp: Optional[int] = None
    tipo: Optional[Literal["gasto","ingreso"]] = None

@router.put("/{record_id}")
def update_record(record_id: str, payload: RecordUpdate = Body(...)):
    db = _load_db()
    items = db.get("items", [])
    idx = next((i for i, r in enumerate(items) if r.get("id") == record_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    found = items[idx]
    if payload.fecha is not None:       found["fecha"] = payload.fecha
    if payload.concepto is not None:    found["concepto"] = payload.concepto
    if payload.categoria is not None:   found["categoria"] = payload.categoria
    if payload.monto_clp is not None:   found["monto_clp"] = int(payload.monto_clp)
    if payload.tipo is not None:        found["tipo"] = payload.tipo

    items[idx] = ensure_schema(found)
    db["items"] = items
    _save_db(db)
    return {"ok": True, "updated": ensure_schema(found)}
