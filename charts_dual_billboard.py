import os, requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

TOKEN   = os.getenv("TG_BOT_TOKEN")
CHAT_ID = int(os.getenv("TG_CHAT_ID", "6210116599"))
HEADLESS = os.getenv("HEADLESS", "1") != "0"

URL_AR = "https://billboard.ar/billboard-charts/"
URL_US = "https://www.billboard.com/charts/hot-100/"

BANNED_AR = {"Contacto", "Compositores:", "Productores:", "Sello discográfico:"}
BANNED_US = {"Songwriter(s):", "Producer(s)", "Imprint/Label", "Distributor:", "Gains in Weekly Performance", "Additional Awards", "Additional Awards ", "Songwriter(s)"}

def send_telegram(text: str):
    if not TOKEN or not CHAT_ID:
        print("⚠️ Falta TG_BOT_TOKEN o TG_CHAT_ID")
        return
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  data={"chat_id": CHAT_ID, "text": text})

def get_top3_msg(url: str, banned: set, titulo: str) -> str:
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,2400")
    opts.add_argument("user-agent=Mozilla/5.0")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 25)
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "h3#title-of-a-story")))
        titles = []
        for e in driver.find_elements(By.CSS_SELECTOR, "h3#title-of-a-story"):
            t = (e.get_attribute("innerText") or e.get_attribute("textContent") or "").strip()
            if t and t not in banned:
                titles.append(t)
        titles = titles[:3]
        artists = [el.get_attribute("innerText").strip() for el in
                   driver.find_elements(By.CSS_SELECTOR, "span.c-label.a-no-trucate.a-color-artist, a.c-label.a-no-trucate.a-link")]
        if len(artists) < 3:
            artists = [el.get_attribute("innerText").strip() for el in
                       driver.find_elements(By.CSS_SELECTOR, "span.c-label.a-no-trucate")]
        artists = [a for a in artists if a][:3]
        n = min(3, len(titles), len(artists))
        if n == 0:
            raise RuntimeError(f"No se pudo extraer Top 3 de {url}")
        top3 = list(zip(titles[:n], artists[:n]))
        return f"🎵 {titulo}\n" + "\n".join(f"{i+1}. {t} — {a}" for i,(t,a) in enumerate(top3))
    finally:
        driver.quit()

if __name__ == "__main__":
    msg_ar = get_top3_msg(URL_AR, BANNED_AR, "Top 3 Billboard Argentina (semana)")
    msg_us = get_top3_msg(URL_US, BANNED_US, "Top 3 Billboard Hot 100 (US)")
    full_msg = msg_ar + "\n\n" + msg_us
    print(full_msg)
    send_telegram(full_msg)
