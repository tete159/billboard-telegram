# server.py
import os, json
from fastapi import FastAPI, Request, HTTPException
import httpx

app = FastAPI()

GH_PAT = os.getenv("GH_PAT")          # PAT con Actions: Read & Write
GH_REPO = os.getenv("GH_REPO")        # ej: "tete159/billboard-telegram"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "hook")
ALLOWED_CHAT_ID = os.getenv("TG_CHAT_ID")  # opcional

def _must_have():
    if not GH_PAT or not GH_REPO:
        raise HTTPException(500, "Missing GH_PAT or GH_REPO")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/trigger/{secret}")
async def trigger(secret: str, chat_id: str):
    _must_have()
    if secret != WEBHOOK_SECRET:
        raise HTTPException(403, "bad secret")
    async with httpx.AsyncClient(timeout=20) as http:
        r = await http.post(
            f"https://api.github.com/repos/{GH_REPO}/dispatches",
            headers={"Authorization": f"Bearer {GH_PAT}",
                     "Accept": "application/vnd.github+json"},
            json={"event_type":"telegram_top",
                  "client_payload":{"chat_id": str(chat_id)}},
        )
    return {"status": r.status_code}

@app.post("/telegram/{secret}")
async def telegram(secret: str, req: Request):
    _must_have()
    if secret != WEBHOOK_SECRET:
        raise HTTPException(403, "bad secret")

    body = await req.json()
    print(">> Telegram update:", json.dumps(body)[:1000])

    msg = body.get("message") or body.get("edited_message") or {}
    chat = msg.get("chat") or {}
    chat_id = str(chat.get("id") or "")

    if ALLOWED_CHAT_ID and chat_id != str(ALLOWED_CHAT_ID):
        print(">> Ignorado por ALLOWED_CHAT_ID")
        return {"ok": True}

    async with httpx.AsyncClient(timeout=20) as http:
        r = await http.post(
            f"https://api.github.com/repos/{GH_REPO}/dispatches",
            headers={"Authorization": f"Bearer {GH_PAT}",
                     "Accept": "application/vnd.github+json"},
            json={"event_type":"telegram_top",
                  "client_payload":{"chat_id": chat_id}},
        )
    print(">> Dispatch to GitHub:", r.status_code, r.text[:200])
    return {"status": r.status_code}

