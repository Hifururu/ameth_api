from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import os, base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from dotenv import load_dotenv
load_dotenv()

from app.integrations.google_oauth import build_flow, save_creds, ensure_creds
from googleapiclient.discovery import build as gbuild

app = FastAPI(title="Ameth API")

@app.get("/health")
def health():
    return {"status": "ok", "service": "ameth", "version": "v1"}

# --- OAuth Google ---
@app.get("/auth/google/start")
def google_auth_start():
    flow = build_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    return {"auth_url": auth_url}

@app.get("/auth/google/callback")
def google_auth_callback(request: Request):
    flow = build_flow()
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(400, "Missing 'code'")
    flow.fetch_token(code=code)
    save_creds(flow.credentials)
    return RedirectResponse(url=os.getenv("APP_BASE_URL", "/") + "/auth/success")

@app.get("/auth/success")
def auth_success():
    return {"ok": True, "msg": "Google conectado"}

# --- Gmail: enviar correo ---
@app.post("/mail/send")
def mail_send(to: str, subject: str, body: str):
    creds, needs = ensure_creds()
    if needs:
        raise HTTPException(401, "Conecta Google: /auth/google/start")
    service = gbuild("gmail", "v1", credentials=creds)
    msg = MIMEText(body, "plain", "utf-8")
    msg["to"] = to; msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"status": "ok", "id": sent.get("id")}

# --- Calendar: crear evento ---
@app.post("/calendar/create")
def calendar_create(
    title: str,
    start_iso: str,
    end_iso: str | None = None,
    description: str | None = None,
    location: str | None = None
):
    creds, needs = ensure_creds()
    if needs:
        raise HTTPException(401, "Conecta Google: /auth/google/start")
    service = gbuild("calendar", "v3", credentials=creds)
    if not end_iso:
        s = datetime.fromisoformat(start_iso.replace("Z","+00:00"))
        end_iso = (s + timedelta(hours=1)).isoformat()
    event = {
        "summary": title,
        "description": description or "",
        "location": location or "",
        "start": {"dateTime": start_iso},
        "end":   {"dateTime": end_iso},
    }
    created = service.events().insert(calendarId="primary", body=event).execute()
    return {"status":"ok","htmlLink": created.get("htmlLink"), "id": created.get("id")}

# --- Notificaciones: WhatsApp / Telegram ---
from app.integrations.messaging import send_whatsapp, send_telegram

class WhatsAppReq(BaseModel):
    to_e164: str
    text: str

@app.post("/notify/whatsapp")
def notify_whatsapp(req: WhatsAppReq):
    return send_whatsapp(req.to_e164, req.text)

class TelegramReq(BaseModel):
    chat_id: str
    text: str

@app.post("/notify/telegram")
def notify_telegram(req: TelegramReq):
    return send_telegram(req.chat_id, req.text)
