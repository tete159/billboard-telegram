# ====== Google Sheets helper ======
import os, json, gspread

# ⚠️ Pega acá tu NUEVO JSON de Service Account (tras rotar la key en GCP).
#    Respetá los \n del private_key tal cual, usando triple comillas.
SERVICE_ACCOUNT_JSON = r"""{
  "type": "service_account",
  "project_id": "TU_PROJECT_ID",
  "private_key_id": "TU_PRIVATE_KEY_ID",
  "private_key": "-----BEGIN PRIVATE KEY-----\nTU_CLAVE_CON_SALTOS\n-----END PRIVATE KEY-----\n",
  "client_email": "tu-sa@tu-proyecto.iam.gserviceaccount.com",
  "client_id": "XXXXXXXXXXXXXXX",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/tu-sa%40tu-proyecto.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}"""

# Fallback del ID del Sheet si no lo pasás por variable de entorno
GSHEET_ID_FALLBACK = "1f6sBU8vWL9nTiUXwNNxNzLcNO1P6UgMrHuoXfnSKSVA"

def _gc():
    raw = os.getenv("GCP_SA_JSON") or SERVICE_ACCOUNT_JSON  # env > hardcode
    info = json.loads(raw)

    # --- Normalización del private_key (por si vino con \\n) ---
    pk = info.get("private_key", "")
    if not pk:
        raise RuntimeError("GCP_SA_JSON: falta private_key")
    if "\\n" in pk and "\n" not in pk:
        pk = pk.replace("\\n", "\n")
    pk = pk.replace("\r\n", "\n").strip()
    if "BEGIN PRIVATE KEY" not in pk or "END PRIVATE KEY" not in pk:
        raise RuntimeError("private_key inválida (faltan encabezados PEM)")
    info["private_key"] = pk
    # ------------------------------------------------------------

    return gspread.service_account_from_dict(info)

def get_gsheet_id():
    return os.getenv("GSHEET_ID") or GSHEET_ID_FALLBACK

def _open_sheet(spreadsheet_id=None):
    sid = spreadsheet_id or get_gsheet_id()
    if not sid:
        raise RuntimeError("Falta GSHEET_ID")
    gc = _gc()
    return gc.open_by_key(sid)

def ensure_headers(ws, headers):
    if not (ws.acell("A1").value or "").strip():
        ws.update("A1", [headers])

def append_rows_dedup(spreadsheet_id=None, worksheet_name="chart_items", rows=None, uniq=("chart","scraped_on","position")):
    """
    rows: lista de dicts (mismas keys). Dedup por (chart, scraped_on, position).
    """
    if not rows:
        print("No hay filas para subir")
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


