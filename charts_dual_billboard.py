# charts_dual_billboard.py
import os, json, requests
from dotenv import load_dotenv
from datetime import date

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

# ==== Telegram ====
TOKEN   = os.getenv("TG_BOT_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")
HEADLESS = os.getenv("HEADLESS", "1") != "0"

# ==== Fuentes ====
URL_AR = "https://billboard.ar/billboard-charts/"
URL_US = "https://www.billboard.com/charts/hot-100/"

BANNED_AR = {"Contacto", "Compositores:", "Productores:", "Sello discográfico:"}
BANNED_US = {"Songwriter(s):", "Producer(s)", "Imprint/Label", "Distributor:",
             "Gains in Weekly Performance", "Additional Awards", "Additional Awards ", "Songwriter(s)"}

def send_telegram(text: str):
    if not TOKEN or not CHAT_ID:
        print(f"⚠️ Falta TG_BOT_TOKEN o TG_CHAT_ID (TOKEN? {bool(TOKEN)} CHAT_ID? {bool(CHAT_ID)})")
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True}
        )
        print("Telegram response:", r.status_code, r.text[:300])
    except Exception as e:
        print("Error enviando a Telegram:", e)

# ==== Scraping genérico: devuelve pares (title, artists) ====
def scrape_pairs(url: str, banned: set, limit: int = 10):
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,2400")
    opts.add_argument("user-agent=Mozilla/5.0")

    d = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    try:
        d.get(url)
        WebDriverWait(d, 25).until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "h3#title-of-a-story")
        ))

        titles = []
        for e in d.find_elements(By.CSS_SELECTOR, "h3#title-of-a-story"):
            t = (e.get_attribute("innerText") or e.get_attribute("textContent") or "").strip()
            if t and t not in banned:
                titles.append(t)

        # artistas (dos variantes)
        artists = [el.get_attribute("innerText").strip() for el in d.find_elements(
            By.CSS_SELECTOR, "span.c-label.a-no-trucate.a-color-artist, a.c-label.a-no-trucate.a-link"
        )]
        if len(artists) < len(titles):
            artists += [el.get_attribute("innerText").strip() for el in d.find_elements(
                By.CSS_SELECTOR, "span.c-label.a-no-trucate"
            )]

        titles  = [t for t in titles  if t][:limit]
        artists = [a for a in artists if a][:limit]
        n = min(len(titles), len(artists))
        if n == 0:
            raise RuntimeError(f"No se pudo extraer datos de {url}")

        return list(zip(titles[:n], artists[:n]))
    finally:
        d.quit()

def compose_msg(title: str, pairs, k=3):
    lines = [f"🎵 {title}"]
    for i, (t, a) in enumerate(pairs[:k], start=1):
        lines.append(f"{i}. {t} — {a}")
    return "\n".join(lines)

# ==== Google Sheets helper (opcional) ====
# Reqs: gspread, google-auth; Secrets: GCP_SA_JSON, GSHEET_ID
def _gc():
    import gspread
    info = json.loads(os.getenv("GCP_SA_JSON", "{}"))
    if not info:
        return None
    return gspread.service_account_from_dict(info)

def _open_sheet(spreadsheet_id):
    gc = _gc()
    if not gc or not spreadsheet_id:
        return None
    return gc.open_by_key(spreadsheet_id)

def ensure_headers(ws, headers):
    if not ws.get('A1'):
        ws.update('A1', [headers])

def append_rows_dedup(spreadsheet_id, worksheet_name, rows, uniq=("chart","scraped_on","position")):
    sh = _open_sheet(spreadsheet_id)
    if not sh or not rows:
        print("Sheets: sin credenciales/ID o sin filas, no subo.")
        return
    import gspread
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet_name, rows="5000", cols="10")

    headers = list(rows[0].keys())
    ensure_headers(ws, headers)

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

def build_rows(chart, url, pairs, top_n=10):
    today = date.today().isoformat()
    out = []
    for i, (t, a) in enumerate(pairs[:top_n], start=1):
        out.append({
            "chart": chart,
            "scraped_on": today,
            "position": i,
            "title": t,
            "artists": a,
            "source_url": url
        })
    return out

# ==== MAIN ====
if __name__ == "__main__":
    # scrape
    ar_pairs = scrape_pairs(URL_AR, BANNED_AR, limit=10)
    us_pairs = scrape_pairs(URL_US, BANNED_US, limit=10)

    # mensaje Telegram (Top 3)
    msg = compose_msg("Top 3 Billboard Argentina (semana)", ar_pairs, 3) + \
          "\n\n" + compose_msg("Top 3 Billboard Hot 100 (US)", us_pairs, 3)
    print(msg)
    send_telegram(msg)

    # subir a Google Sheets (Top 10)
    rows = []
    rows += build_rows("AR Hot 100", URL_AR, ar_pairs, top_n=10)
    rows += build_rows("US Hot 100", URL_US, us_pairs, top_n=10)
    append_rows_dedup(
        spreadsheet_id=os.getenv("GSHEET_ID"),
        worksheet_name="chart_items",
        rows=rows
    )

