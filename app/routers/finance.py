from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime, timezone
import json, os
from pathlib import Path
import secrets

# ==== Seguridad simple por API Key (igual que antes) ====
API_KEY = os.environ.get("API_XKEY", "prod-xyz")

def check_key(x_api_key: Optional[str]):
    if not secrets.compare_digest((x_api_key or ""), API_KEY):
        raise HTTPException(status_code=401, detail="Unauthorized")

# ==== Storage (JSON en disco, retro-compatible) ====
DB_PATH = Path(os.environ.get("AMETH_DB_FILE", "data/finance.json"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def _ulid_like() -> str:
    # Suficientemente único para este caso (puedes cambiar a 'ulid-py' si quieres)
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") + secrets.token_hex(4)

def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _load_db() -> List[dict]:
    if not DB_PATH.exists():
        return []
    try:
        with DB_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "items" in data:
                data = data["items"]  # compat con formato antiguo {"items":[...]}
            if not isinstance(data, list):
                return []
            # Asegura campos nuevos en registros antiguos
            changed = False
            for it in data:
                if "id" not in it:
                    it["id"] = _ulid_like()
                    changed = True
                if "is_deleted" not in it:
                    it["is_deleted"] = False
                    changed = True
                if "deleted_at" not in it:
                    it["deleted_at"] = None
                    changed = True
            if changed:
                _save_db(data)
            return data
    except Exception:
        return []

def _save_db(items: List[dict]):
    with DB_PATH.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

# ==== Esquemas ====
TipoMovimiento = Literal["gasto", "ingreso"]

class MovimientoIn(BaseModel):
    fecha: str  # "YYYY-MM-DD"
    concepto: str
    categoria: str
    monto_clp: int = Field(ge=0)
    tipo: TipoMovimiento

class Movimiento(BaseModel):
    id: str
    fecha: str
    concepto: str
    categoria: str
    monto_clp: int
    tipo: TipoMovimiento
    is_deleted: bool = False
    deleted_at: Optional[str] = None

class ListResponse(BaseModel):
    items: List[Movimiento]

class SummaryResponse(BaseModel):
    gastos: int
    ingresos: int
    balance: int

router = APIRouter(prefix="/finance", tags=["finance"])

# ==== ENDPOINTS ====

@router.post("/record", response_model=dict)
def record(mov: MovimientoIn, x_api_key: Optional[str] = Header(None)):
    check_key(x_api_key)
    items = _load_db()
    new_item = {
        "id": _ulid_like(),
        "fecha": mov.fecha,
        "concepto": mov.concepto,
        "categoria": mov.categoria,
        "monto_clp": mov.monto_clp,
        "tipo": mov.tipo,
        "is_deleted": False,
        "deleted_at": None,
    }
    items.append(new_item)
    _save_db(items)
    return {"ok": True, "id": new_item["id"]}

@router.get("/list", response_model=ListResponse)
def list_items(include_deleted: bool = Query(False), x_api_key: Optional[str] = Header(None)):
    check_key(x_api_key)
    items = _load_db()
    if not include_deleted:
        items = [it for it in items if not it.get("is_deleted", False)]
    # Ordena descendente por fecha + id (opcional)
    items.sort(key=lambda it: (it.get("fecha",""), it.get("id","")), reverse=True)
    return {"items": items}

@router.get("/summary", response_model=SummaryResponse)
def summary(month: Optional[str] = Query(None, description='YYYY-MM (ej: "2025-09")'),
            x_api_key: Optional[str] = Header(None)):
    check_key(x_api_key)
    items = [it for it in _load_db() if not it.get("is_deleted", False)]
    if month:
        prefix = month + "-"
        items = [it for it in items if str(it.get("fecha","")).startswith(prefix)]
    gastos = sum(it["monto_clp"] for it in items if it["tipo"] == "gasto")
    ingresos = sum(it["monto_clp"] for it in items if it["tipo"] == "ingreso")
    return {"gastos": gastos, "ingresos": ingresos, "balance": ingresos - gastos}

@router.delete("/{mov_id}", response_model=dict)
def delete_mov(mov_id: str, hard: bool = Query(False), x_api_key: Optional[str] = Header(None)):
    """
    Por defecto hace SOFT DELETE (oculta). Si hard=true, elimina físicamente.
    """
    check_key(x_api_key)
    items = _load_db()
    idx = next((i for i, it in enumerate(items) if it.get("id") == mov_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    if hard:
        items.pop(idx)
        _save_db(items)
        return {"ok": True, "deleted": "hard"}
    else:
        items[idx]["is_deleted"] = True
        items[idx]["deleted_at"] = _now_utc_iso()
        _save_db(items)
        return {"ok": True, "deleted": "soft"}

@router.patch("/{mov_id}/restore", response_model=dict)
def restore_mov(mov_id: str, x_api_key: Optional[str] = Header(None)):
    check_key(x_api_key)
    items = _load_db()
    idx = next((i for i, it in enumerate(items) if it.get("id") == mov_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    items[idx]["is_deleted"] = False
    items[idx]["deleted_at"] = None
    _save_db(items)
    return {"ok": True, "restored": True}
