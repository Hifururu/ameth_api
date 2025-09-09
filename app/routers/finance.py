from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List
from datetime import datetime, date
import os, json, threading

DATA_PATH = os.environ.get("AMETH_DATA_PATH", "data")
RECORDS_FILE = os.path.join(DATA_PATH, "records.json")
_lock = threading.Lock()

class RecordType(str, Enum):
    gasto = "gasto"
    ingreso = "ingreso"

class RecordIn(BaseModel):
    date: date
    concept: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    amount_clp: int = Field(..., ge=0)
    type: RecordType
    source: Optional[str] = None
    external_id: Optional[str] = None

class RecordOut(RecordIn):
    id: str
    hidden: bool = False

def _ensure_store():
    os.makedirs(DATA_PATH, exist_ok=True)
    if not os.path.exists(RECORDS_FILE):
        with open(RECORDS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)

def _load() -> List[dict]:
    _ensure_store()
    with open(RECORDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(items: List[dict]):
    tmp = RECORDS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2, default=str)
    os.replace(tmp, RECORDS_FILE)

router = APIRouter()

@router.get("/records", summary="Listar registros por mes")
def list_records(month: str = Query(..., regex=r"^\d{4}-\d{2}$")) -> List[RecordOut]:
    y, m = [int(x) for x in month.split("-")]
    with _lock:
        items = _load()
    pref = f"{y:04d}-{m:02d}"
    return [x for x in items if str(x.get("date","")).startswith(pref) and not x.get("hidden", False)]

@router.post("/records", summary="Crear registro", response_model=RecordOut)
def create_record(rec: RecordIn):
    with _lock:
        items = _load()
        new_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        new = {
            "id": new_id,
            "date": rec.date.isoformat(),
            "concept": rec.concept,
            "category": rec.category,
            "amount_clp": rec.amount_clp,
            "type": rec.type.value,
            "source": rec.source,
            "external_id": rec.external_id,
            "hidden": False,
        }
        items.append(new)
        _save(items)
    return new

@router.delete("/records/{rec_id}", summary="Ocultar o borrar registro")
def hide_or_delete_record(rec_id: str, hard: bool = False):
    with _lock:
        items = _load()
        idx = next((i for i, x in enumerate(items) if x.get("id")==rec_id), None)
        if idx is None:
            raise HTTPException(status_code=404, detail="Not Found")
        if hard:
            items.pop(idx)
        else:
            items[idx]["hidden"] = True
        _save(items)
    return {"ok": True}
