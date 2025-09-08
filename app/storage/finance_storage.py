import os, json, uuid, hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple

DATA_DIR = os.environ.get("DATA_DIR", "/data")
FINANCE_PATH = os.path.join(DATA_DIR, "finance")
DB_FILE = os.path.join(FINANCE_PATH, "records.json")

def _ensure_dirs():
    os.makedirs(FINANCE_PATH, exist_ok=True)
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({"items": []}, f, ensure_ascii=False)

def _load_db() -> Dict:
    _ensure_dirs()
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_db(db: Dict):
    tmp = DB_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False)
    os.replace(tmp, DB_FILE)

def _normalize_str(x: str) -> str:
    return " ".join((x or "").strip().lower().split())

def compute_idem_key(fecha: str, concepto: str, categoria: str, monto_clp: int, tipo: str) -> str:
    raw = "|".join([
        _normalize_str(fecha),
        _normalize_str(concepto),
        _normalize_str(categoria),
        str(int(monto_clp)),
        _normalize_str(tipo),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def ensure_schema(r: Dict) -> Dict:
    # Migra registros antiguos: añade id/created_at/idem_key en base a campos existentes.
    r = dict(r)
    if "id" not in r or not r.get("id"):
        r["id"] = str(uuid.uuid4())
    if "created_at" not in r or not r.get("created_at"):
        # si hay 'ts' antiguo, úsalo; si no, ahora.
        created = r.get("ts")
        if created:
            # normaliza a ISO con Z si viene como "YYYY-MM-DD HH:MM:SS"
            if "T" not in created:
                created = created.replace(" ", "T") + "Z"
            r["created_at"] = created
        else:
            r["created_at"] = datetime.utcnow().isoformat() + "Z"
    if "idem_key" not in r or not r.get("idem_key"):
        r["idem_key"] = compute_idem_key(
            r.get("fecha",""),
            r.get("concepto",""),
            r.get("categoria",""),
            int(r.get("monto_clp", 0)),
            r.get("tipo",""),
        )
    return r

def add_record(fecha: str, concepto: str, categoria: str, monto_clp: int, tipo: str,
               enforce_idempotency: bool = True) -> Tuple[Dict, bool]:
    db = _load_db()
    db["items"] = [ensure_schema(x) for x in db.get("items", [])]

    idem_key = compute_idem_key(fecha, concepto, categoria, monto_clp, tipo)
    if enforce_idempotency:
        for it in db["items"]:
            if it.get("idem_key") == idem_key:
                _save_db(db)
                return it, False

    rec = ensure_schema({
        "fecha": fecha,
        "concepto": concepto,
        "categoria": categoria,
        "monto_clp": int(monto_clp),
        "tipo": tipo,
    })
    db["items"].append(rec)
    _save_db(db)
    return rec, True

def list_records(month: Optional[str] = None) -> List[Dict]:
    db = _load_db()
    items = [ensure_schema(x) for x in db.get("items", [])]
    if not month:
        return sorted(items, key=lambda x: (x.get("fecha",""), x.get("created_at","")))
    pref = month + "-"
    return sorted([x for x in items if x.get("fecha","").startswith(pref)],
                  key=lambda x: (x.get("fecha",""), x.get("created_at","")))

def summary_month(month: str) -> Dict:
    items = list_records(month=month)
    gastos = sum(x["monto_clp"] for x in items if x.get("tipo") == "gasto")
    ingresos = sum(x["monto_clp"] for x in items if x.get("tipo") == "ingreso")
    return {"month": month, "count": len(items), "ingresos": ingresos, "gastos": gastos, "saldo": ingresos - gastos}

def delete_record(record_id: str) -> bool:
    db = _load_db()
    items = [ensure_schema(x) for x in db.get("items", [])]
    new_items = [x for x in items if x.get("id") != record_id]
    if len(new_items) == len(items):
        return False
    db["items"] = new_items
    _save_db(db)
    return True

def clear_month(month: str) -> int:
    db = _load_db()
    items = [ensure_schema(x) for x in db.get("items", [])]
    keep = [x for x in items if not x.get("fecha","").startswith(month + "-")]
    removed = len(items) - len(keep)
    db["items"] = keep
    _save_db(db)
    return removed

def dedupe_month(month: str) -> int:
    """Quita duplicados dentro del mes según idem_key (conserva el primero cronológico)."""
    db = _load_db()
    items = [ensure_schema(x) for x in db.get("items", [])]
    pref = month + "-"
    seen = set()
    keep, removed = [], 0
    for r in sorted(items, key=lambda x: (x.get("fecha",""), x.get("created_at",""))):
        if r.get("fecha","").startswith(pref):
            key = r.get("idem_key")
            if key in seen:
                removed += 1
                continue
            seen.add(key)
        keep.append(r)
    db["items"] = keep
    _save_db(db)
    return removed

def export_month(month: str, fmt: str = "csv") -> Tuple[bytes, str, str]:
    rows = list_records(month=month)
    if fmt.lower() == "csv":
        import io, csv
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["id","fecha","concepto","categoria","monto_clp","tipo","created_at"])
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "id": r.get("id",""),
                "fecha": r.get("fecha",""),
                "concepto": r.get("concepto",""),
                "categoria": r.get("categoria",""),
                "monto_clp": r.get("monto_clp",0),
                "tipo": r.get("tipo",""),
                "created_at": r.get("created_at",""),
            })
        return buf.getvalue().encode("utf-8"), "text/csv; charset=utf-8", f"finance-{month}.csv"
    elif fmt.lower() == "xlsx":
        try:
            from openpyxl import Workbook
        except Exception:
            raise RuntimeError("xlsx no disponible: instala 'openpyxl'")
        wb = Workbook()
        ws = wb.active
        ws.append(["id","fecha","concepto","categoria","monto_clp","tipo","created_at"])
        for r in rows:
            ws.append([
                r.get("id",""), r.get("fecha",""), r.get("concepto",""),
                r.get("categoria",""), r.get("monto_clp",0), r.get("tipo",""),
                r.get("created_at",""),
            ])
        import io
        bio = io.BytesIO()
        wb.save(bio)
        return bio.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"finance-{month}.xlsx"
    else:
        raise ValueError("Formato no soportado. Usa csv o xlsx.")
