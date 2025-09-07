# app/integrations/telegram.py
import os
import requests
from typing import Optional

class TelegramConfigError(RuntimeError):
    pass

def _get_config():
    token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token:
        raise TelegramConfigError("Falta TELEGRAM_BOT_TOKEN/TELEGRAM_TOKEN")
    if not chat_id:
        raise TelegramConfigError("Falta TELEGRAM_CHAT_ID")
    base_url = f"https://api.telegram.org/bot{token}"
    return base_url, chat_id

def send_message(text: str, chat_id: Optional[str] = None) -> dict:
    base_url, default_chat = _get_config()
    cid = chat_id or default_chat
    url = f"{base_url}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": cid, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
