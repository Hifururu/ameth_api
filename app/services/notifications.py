# app/services/notifications.py
import os
from datetime import date
from zoneinfo import ZoneInfo
from app.integrations.telegram import send_message
from app.storage.db import summary_month

TZ = ZoneInfo("America/Santiago")
NOTIFY_ENABLED = os.getenv("TELEGRAM_NOTIFY", "true").lower() == "true"

def _fmt_money(n: int) -> str:
    return f"${n:,}".replace(",", ".")

def notify_finance_event(tipo: str, concepto: str, monto_clp: int, categoria: str):
    if not NOTIFY_ENABLED:
        return
    try:
        from datetime import datetime
        ahora = datetime.now(TZ).strftime("%d-%m %H:%M")
        signo = "-" if tipo.lower() == "gasto" else "+"
        msg = (
            f"<b>{'Gasto' if tipo.lower()=='gasto' else 'Ingreso'} registrado</b>\n"
            f"{ahora}\n"
            f"• {concepto} ({categoria})\n"
            f"• Monto: {signo}{_fmt_money(monto_clp)}"
        )
        send_message(msg)
    except Exception:
        pass

def daily_greeting_summary():
    if not NOTIFY_ENABLED:
        return
    try:
        hoy = date.today()
        mes = hoy.strftime("%Y-%m")
        s = summary_month(mes)

        msg = (
            f"<b>Resumen diario — {hoy.strftime('%d-%m-%Y')}</b>\n"
            f"Mes: <code>{mes}</code>\n"
            f"• Ingresos: {_fmt_money(s['ingresos'])}\n"
            f"• Gastos: {_fmt_money(s['gastos'])}\n"
            f"• Saldo: {_fmt_money(s['saldo'])}\n"
            "\n¿Deseas registrar un gasto/ingreso ahora?"
        )
        send_message(msg)
    except Exception:
        pass
