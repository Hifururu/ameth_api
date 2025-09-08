# app/security/auth.py
import os
from typing import Set
from fastapi import Header, HTTPException, status

def _get_keys() -> Set[str]:
    """
    Lee claves válidas desde API_KEYS (coma-separadas) o API_KEY.
    Ej: API_KEYS="dev123,prod-456"
    """
    raw = os.getenv("API_KEYS") or os.getenv("API_KEY") or ""
    return {k.strip() for k in raw.split(",") if k.strip()}

async def api_key_auth(x_api_key: str | None = Header(None, alias="x-api-key")):
    keys = _get_keys()
    if not keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key no configurada en el servidor",
        )
    if not x_api_key or x_api_key not in keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida o ausente",
        )
    return True
