import os
from dataclasses import dataclass

def _req(name):
    v = os.getenv(name)
    return v.strip() if v and v.strip() else None

@dataclass
class Settings:
    qx_email: str
    qx_password: str
    frontend_origin: str
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    host: str
    port: int

def load_settings():
    email = _req("QX_EMAIL")
    pw = _req("QX_PASSWORD")
    if not email or not pw:
        raise RuntimeError("Set QX_EMAIL and QX_PASSWORD in .env")
    return Settings(
        qx_email=email,
        qx_password=pw,
        frontend_origin=os.getenv("FRONTEND_ORIGIN", "https://rahulmondaljr-creator.github.io"),
        telegram_bot_token=_req("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_req("TELEGRAM_CHAT_ID"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
    )

settings = load_settings()
