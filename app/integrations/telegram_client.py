import os
import requests
from typing import Optional

# Compatibilidad: acepta TELEGRAM_BOT_TOKEN o TELEGRAM_TOKEN
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else None

class TelegramConfigError(RuntimeError):
    pass

def send_message(text: str, chat_id: Optional[str] = None) -> dict:
    """
    Envía un mensaje a Telegram. Usa variables de entorno:
    TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID.
    """
    if not BOT_TOKEN or not BASE_URL:
        raise TelegramConfigError("Falta TELEGRAM_BOT_TOKEN/TELEGRAM_TOKEN")
    cid = chat_id or CHAT_ID
    if not cid:
        raise TelegramConfigError("Falta TELEGRAM_CHAT_ID")
    url = f"{BASE_URL}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": cid, "text": text, "parse_mode": "HTML"},
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()
