import os
from fastapi import FastAPI, Request, HTTPException
import httpx

app = FastAPI()

# ---- Config ----
TG_TOKEN = os.getenv("TG_BOT_TOKEN")              # token del bot
ALLOWED_CHAT_ID = os.getenv("TG_CHAT_ID")         # opcional: limita el uso
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "hook")  # segmento secreto de la URL

GH_PAT   = os.getenv("GH_PAT")                    # PAT de GitHub (scope: workflow)
GH_REPO  = os.getenv("GH_REPO")                   # ej: "tete159/billboard-telegram"
GH_BRANCH = os.getenv("GH_BRANCH", "main")

@app.post(f"/telegram/{WEBHOOK_SECRET}")
async def telegram_update(req: Request):
    if not (TG_TOKEN and GH_PAT and GH_REPO):
        raise HTTPException(500, "Faltan env vars")

    payload = await req.json()
    msg = payload.get("message") or payload.get("edited_message") or {}
    chat = msg.get("chat", {})
    chat_id = str(chat.get("id", ""))
    text = (msg.get("text") or "").strip()

    # opcional: solo vos
    if ALLOWED_CHAT_ID and chat_id != str(ALLOWED_CHAT_ID):
        return {"ok": True}

    # ¿cuándo disparar? acá: cualquier mensaje o solo /top
    if not text or (text and not text.startswith(("/", "."))):
        # dispara aunque no haya comando; ajustá a gusto
        pass

    # Disparar repository_dispatch con el chat_id como client_payload
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.post(
            f"https://api.github.com/repos/{GH_REPO}/dispatches",
            headers={
                "Authorization": f"Bearer {GH_PAT}",
                "Accept": "application/vnd.github+json",
            },
            json={
                "event_type": "telegram_top",
                "client_payload": {"chat_id": chat_id}
            },
        )
    return {"status": r.status_code}
