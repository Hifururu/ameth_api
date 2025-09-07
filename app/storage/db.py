# app/storage/db.py
import os
import sqlite3
from typing import List, Dict

DATA_DIR = os.getenv("DATA_DIR", "/data")
DB_PATH = os.path.join(DATA_DIR, "ameth.sqlite3")

def _conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    with _conn() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS finance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,          -- YYYY-MM-DD
            concepto TEXT NOT NULL,
            categoria TEXT NOT NULL,
            monto_clp INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('gasto','ingreso')),
            ts TEXT NOT NULL              -- ISO timestamp UTC
        );
        """)
        con.commit()

def insert_record(rec: Dict):
    with _conn() as con:
        con.execute(
            "INSERT INTO finance_records (fecha, concepto, categoria, monto_clp, tipo, ts) VALUES (?,?,?,?,?,?)",
            (rec["fecha"], rec["concepto"], rec["categoria"], rec["monto_clp"], rec["tipo"], rec["ts"])
        )
        con.commit()

def list_records() -> List[Dict]:
    with _conn() as con:
        cur = con.execute("SELECT fecha, concepto, categoria, monto_clp, tipo, ts FROM finance_records ORDER BY ts ASC")
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

def summary_month(month: str) -> Dict:
    # month = "YYYY-MM"
    with _conn() as con:
        cur_g = con.execute(
            "SELECT COALESCE(SUM(monto_clp),0) FROM finance_records WHERE tipo='gasto' AND substr(fecha,1,7)=?",
            (month,)
        )
        cur_i = con.execute(
            "SELECT COALESCE(SUM(monto_clp),0) FROM finance_records WHERE tipo='ingreso' AND substr(fecha,1,7)=?",
            (month,)
        )
        gastos = cur_g.fetchone()[0]
        ingresos = cur_i.fetchone()[0]
        return {"month": month, "ingresos": ingresos, "gastos": gastos, "saldo": ingresos - gastos}
