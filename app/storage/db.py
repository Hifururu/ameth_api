# app/storage/db.py
import os
import sqlite3
from typing import Any, Dict, List

DB_DIR = os.getenv("DATA_DIR", "./data").strip() or "./data"
DB_PATH = os.path.join(DB_DIR, "ameth.sqlite3")

def _ensure_db() -> None:
    os.makedirs(DB_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        # Tabla principal
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS finance_items (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha      TEXT    NOT NULL,                   -- 'YYYY-MM-DD'
                concepto   TEXT    NOT NULL,
                categoria  TEXT    NOT NULL,
                tipo       TEXT    NOT NULL CHECK (tipo IN ('gasto','ingreso')),
                monto_clp  INTEGER NOT NULL,
                ts         TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
            """
        )
        # Migración defensiva: agrega ts si faltara
        cur.execute("PRAGMA table_info(finance_items)")
        cols = {row[1] for row in cur.fetchall()}
        if "ts" not in cols:
            cur.execute("ALTER TABLE finance_items ADD COLUMN ts TEXT NOT NULL DEFAULT (datetime('now','localtime'))")
        conn.commit()

def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}

def record_item(item: Dict[str, Any]) -> bool:
    """
    Inserta un registro de finanzas.
    item = {
        'fecha': 'YYYY-MM-DD', 'concepto': str, 'categoria': str,
        'tipo': 'gasto'|'ingreso', 'monto_clp': int
    }
    """
    _ensure_db()
    required = {"fecha", "concepto", "categoria", "tipo", "monto_clp"}
    if not required.issubset(item.keys()):
        raise ValueError(f"Faltan campos: {required - set(item.keys())}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO finance_items (fecha, concepto, categoria, tipo, monto_clp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(item["fecha"]),
                str(item["concepto"]),
                str(item["categoria"]),
                str(item["tipo"]),
                int(item["monto_clp"]),
            ),
        )
        conn.commit()
    return True

def list_items() -> List[Dict[str, Any]]:
    """Retorna todos los items (más nuevos primero)."""
    _ensure_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT fecha, concepto, categoria, tipo, monto_clp, ts
            FROM finance_items
            ORDER BY datetime(ts) DESC, id DESC
            """
        )
        rows = cur.fetchall()
        return [_row_to_dict(r) for r in rows]

def month_summary(month: str) -> Dict[str, Any]:
    """
    Devuelve resumen del mes 'YYYY-MM':
    { 'month': 'YYYY-MM', 'ingresos': int, 'gastos': int, 'saldo': int }
    """
    _ensure_db()
    prefix = f"{month}-"
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # Sumatorias por tipo usando LIKE en fecha o ts
        cur.execute(
            """
            SELECT
              SUM(CASE WHEN tipo='ingreso' THEN monto_clp ELSE 0 END) AS ingresos,
              SUM(CASE WHEN tipo='gasto'   THEN monto_clp ELSE 0 END) AS gastos
            FROM finance_items
            WHERE fecha LIKE ? OR ts LIKE ?
            """,
            (prefix + "%", month + "%"),
        )
        row = cur.fetchone() or {"ingresos": 0, "gastos": 0}
        ingresos = int(row["ingresos"] or 0)
        gastos   = int(row["gastos"] or 0)
        return {"month": month, "ingresos": ingresos, "gastos": gastos, "saldo": ingresos - gastos}
