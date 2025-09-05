import os, pathlib
from typing import Tuple
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

SCOPES = os.getenv("GOOGLE_SCOPES", "").split()
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
TOKENS_DIR = pathlib.Path("./data/tokens"); TOKENS_DIR.mkdir(parents=True, exist_ok=True)
TOKEN_PATH = TOKENS_DIR / "google_token.json"

def build_flow() -> Flow:
    return Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

def save_creds(creds: Credentials):
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

def load_creds() -> Credentials | None:
    if TOKEN_PATH.exists():
        return Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    return None

def ensure_creds() -> Tuple[Credentials, bool]:
    creds = load_creds()
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            save_creds(creds)
            return creds, False
        return None, True
    return creds, False
