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
