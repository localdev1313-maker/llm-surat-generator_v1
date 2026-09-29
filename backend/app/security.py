"""
Autentikasi HTTP Basic untuk seluruh endpoint API.

- Aktif hanya bila AUTH_USERNAME dan AUTH_PASSWORD keduanya diset (env/.env).
  Bila tidak, semua endpoint terbuka (mode lama) — startup mencatat warning.
- /api/health SELALU terbuka agar tombol "Tes Koneksi" aplikasi bekerja
  sebelum login.
- Bot Telegram tidak melewati HTTP sehingga tidak terpengaruh.

Pemakaian pada router:
    app.include_router(surat.router, dependencies=[Depends(require_auth)])
"""
import base64
import hmac
import logging

from fastapi import Depends, HTTPException, Request
from fastapi.security.utils import get_authorization_scheme_param

from .config import settings

logger = logging.getLogger(__name__)


def require_auth(request: Request) -> None:
    """Dependency FastAPI: validasi Authorization: Basic bila auth aktif."""
    if not settings.auth_enabled:
        return

    authorization = request.headers.get("Authorization", "")
    scheme, param = get_authorization_scheme_param(authorization)
    if scheme.lower() != "basic" or not param:
        raise _unauthorized()

    try:
        decoded = base64.b64decode(param).decode("utf-8")
    except Exception:
        raise _unauthorized()

    username, _, password = decoded.partition(":")
    # compare_digest mencegah timing attack pada perbandingan kredensial
    user_ok = hmac.compare_digest(username.encode(), settings.AUTH_USERNAME.encode())
    pass_ok = hmac.compare_digest(password.encode(), settings.AUTH_PASSWORD.encode())
    if not (user_ok and pass_ok):
        raise _unauthorized()


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Autentikasi diperlukan (Basic Auth)",
        headers={"WWW-Authenticate": "Basic"},
    )
