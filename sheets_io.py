# sheets_io.py
import os, json, gspread

# ⚠️ SOLO si insistís en hardcodear:
SERVICE_ACCOUNT_JSON = r"""{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...TU CLAVE...\n-----END PRIVATE KEY-----\n",
  "client_email": "...@....iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "...",
  "universe_domain": "googleapis.com"
}"""

def _gc():
    raw = os.getenv("GCP_SA_JSON") or SERVICE_ACCOUNT_JSON  # <-- fallback
    info = json.loads(raw)
    return gspread.service_account_from_dict(info)

def _open_sheet(spreadsheet_id):
    if not spreadsheet_id:
        raise RuntimeError("Falta GSHEET_ID")
    gc = _gc()
    return gc.open_by_key(spreadsheet_id)

def ensure_headers(ws, headers):
    if not (ws.acell("A1").value or "").strip():
        ws.update("A1", [headers])

def append_rows_dedup(spreadsheet_id, worksheet_name, rows, uniq=("chart","scraped_on","position")):
    """
    rows: lista de dicts (mismas keys). Dedup por (chart, scraped_on, position).
    """
    if not rows:
        print("No hay filas para subir"); 
        return

    sh = _open_sheet(spreadsheet_id)
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet_name, rows="5000", cols="10")

    headers = list(rows[0].keys())
    ensure_headers(ws, headers)

    existing = ws.get_all_records()  # usa fila 1 como headers
    seen = {tuple(str(r.get(k, "")) for k in uniq) for r in existing}

    new_values = []
    for r in rows:
        key = tuple(str(r.get(k, "")) for k in uniq)
        if key in seen:
            continue
        new_values.append([r.get(h, "") for h in headers])

    if new_values:
        ws.append_rows(new_values, value_input_option="RAW")
        print(f"✅ Agregadas {len(new_values)} filas en '{worksheet_name}'")
    else:
        print("ℹ️ Nada nuevo (dedup)")

