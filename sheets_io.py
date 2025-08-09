# sheets_io.py
import os, json, gspread

def _gc():
    raw = os.getenv("GCP_SA_JSON")
    if not raw:
        raise RuntimeError("Falta GCP_SA_JSON")
    info = json.loads(raw)

    pk = info.get("private_key", "")
    if not pk:
        raise RuntimeError("GCP_SA_JSON: falta private_key")
    if "\\n" in pk and "\n" not in pk:
        pk = pk.replace("\\n", "\n")
    pk = pk.replace("\r\n", "\n").strip()
    if "BEGIN PRIVATE KEY" not in pk or "END PRIVATE KEY" not in pk:
        raise RuntimeError("private_key inválida (faltan encabezados PEM)")

    info["private_key"] = pk
    return gspread.service_account_from_dict(info)

def _open_sheet(spreadsheet_id):
    if not spreadsheet_id:
        raise RuntimeError("Falta GSHEET_ID")
    gc = _gc()
    return gc.open_by_key(spreadsheet_id)


def get_gsheet_id():
    return os.getenv("GSHEET_ID") or GSHEET_ID_FALLBACK

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


