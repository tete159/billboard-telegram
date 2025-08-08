import os, time, requests
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
CHAT_ID = os.getenv("TG_CHAT_ID")
HEADLESS = os.getenv("HEADLESS", "1") != "0"

URL_AR = "https://billboard.ar/billboard-charts/"
URL_US = "https://www.billboard.com/charts/hot-100/"

def send(text):
    if not TOKEN or not CHAT_ID: 
        print("⚠️ Falta TG_BOT_TOKEN o TG_CHAT_ID"); return
    r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True})
    print("Telegram response:", r.status_code, r.text[:200])

def _driver():
    o = Options()
    if HEADLESS: o.add_argument("--headless=new")
    o.add_argument("--no-sandbox"); o.add_argument("--disable-dev-shm-usage")
    o.add_argument("--window-size=1280,2400"); o.add_argument("user-agent=Mozilla/5.0")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=o)

def scrape_top_n(url, n=10):
    d = _driver()
    try:
        d.get(url)
        WebDriverWait(d,25).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,"ul.o-chart-results-list")))
        # elegir el UL con más LI
        best = max(d.find_elements(By.CSS_SELECTOR,"ul.o-chart-results-list"),
                   key=lambda ul: len(ul.find_elements(By.CSS_SELECTOR,"li.o-chart-results-list__item")))
        out=[]
        for li in best.find_elements(By.CSS_SELECTOR,"li.o-chart-results-list__item"):
            if len(out) >= n: break
            title, artists = "", ""
            try:
                h3 = li.find_element(By.CSS_SELECTOR,"h3#title-of-a-story")
                title = (h3.get_attribute("innerText") or h3.text or "").strip()
            except: pass
            nodes = li.find_elements(By.CSS_SELECTOR,"span.c-label.a-no-trucate.a-color-artist, a.c-label.a-no-trucate.a-link")
            if not nodes:
                nodes = li.find_elements(By.CSS_SELECTOR,"span.c-label.a-no-trucate")
            artists = ", ".join((x.get_attribute("innerText") or x.text or "").strip() for x in nodes if (x.get_attribute("innerText") or x.text or "").strip())
            if title:
                out.append((title, artists))
        return out
    finally:
        d.quit()

if __name__ == "__main__":
    ar = scrape_top_n(URL_AR, 10)
    us = scrape_top_n(URL_US, 10)
    msg = "🇦🇷 Top 10 Billboard Argentina\n" + "\n".join(f"{i+1}. {t} — {a}" if a else f"{i+1}. {t}" for i,(t,a) in enumerate(ar))
    msg += "\n\n🇺🇸 Top 10 Billboard Hot 100\n" + "\n".join(f"{i+1}. {t} — {a}" if a else f"{i+1}. {t}" for i,(t,a) in enumerate(us))
    print(msg)
    send(msg)

