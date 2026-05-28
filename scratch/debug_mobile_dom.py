import time
import os
import re
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def parse_heuristics(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    found = []
    for el in soup.find_all(class_=True):
        classes = el.get("class", [])
        cls_str = " ".join(classes).lower()
        if any(k in cls_str for k in ["gdas", "review"]):
            found.append(f"Tag: {el.name}, Class: {classes}, Text: {el.text.strip()[:100]}")
    return found

def main():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=375,812")
    options.binary_location = EDGE_BINARY_PATH
    options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")
    
    driver = webdriver.Edge(options=options)
    logs = []
    
    try:
        url = "https://m.oliveyoung.co.kr/m/goods/getGoodsDetail.do?goodsNo=A000000166709"
        logs.append(f"[*] Loading {url}")
        driver.get(url)
        time.sleep(5)
        
        # Click reviews tab
        buttons = driver.find_elements(By.XPATH, "//*[contains(text(), '리뷰')]")
        for btn in buttons:
            try:
                driver.execute_script("arguments[0].click();", btn)
                logs.append(f"[+] Clicked review tab: {btn.text}")
                time.sleep(3)
                break
            except Exception as e:
                logs.append(f"[-] Click failed: {e}")
                
        # Scroll gradually and capture review elements
        logs.append("[*] Scrolling gradually...")
        for step in range(5):
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(2)
            html = driver.page_source
            items = parse_heuristics(html)
            logs.append(f"--- Step {step} | Scroll Y: {driver.execute_script('return window.scrollY;')} ---")
            logs.append(f"Found {len(items)} review-related elements in DOM.")
            for item in items[:15]:
                logs.append(f"  {item}")
                
    finally:
        driver.quit()
        
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(script_dir, "debug_dom_output.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(logs))
    print(f"[*] Wrote output to {out_path}")

if __name__ == "__main__":
    main()
