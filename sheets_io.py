# ====== Google Sheets helper ======
import os, json, gspread
from datetime import date

def _gc():
    info = json.loads(os.getenv("GCP_SA_JSON"))
    return gspread.service_account_from_dict(info)

def _open_sheet(spreadsheet_id):
    gc = _gc()
    return gc.open_by_key(spreadsheet_id)

def ensure_headers(ws, headers):
    if not ws.get('A1'):  # si no hay cabecera
        ws.update('A1', [headers])

def append_rows_dedup(spreadsheet_id, worksheet_name, rows, uniq=("chart","scraped_on","position")):
    """
    rows: lista de dicts con mismas keys (p.ej. chart, scraped_on, position, title, artists, source_url)
    Dedup por (chart, scraped_on, position).
    """
    if not rows:
        print("No hay filas para subir"); return

    sh = _open_sheet(spreadsheet_id)
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet_name, rows="5000", cols="10")

    headers = list(rows[0].keys())
    ensure_headers(ws, headers)

    # leo existentes para dedup (ok para top10 diario; si crece mucho, optimizamos)
    existing = ws.get_all_records()
    seen = {tuple(str(r[k]) for k in uniq) for r in existing}

    new_values = []
    for r in rows:
        key = tuple(str(r[k]) for k in uniq)
        if key in seen:
            continue
        new_values.append([r.get(h, "") for h in headers])

    if new_values:
        ws.append_rows(new_values, value_input_option="RAW")
        print(f"✅ Agregadas {len(new_values)} filas en '{worksheet_name}'")
    else:
        print("ℹ️ Nada nuevo (dedup)")
