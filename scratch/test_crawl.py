import time
import os
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By

EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def main():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=375,812")
    options.binary_location = EDGE_BINARY_PATH
    
    # Set mobile user agent
    options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")
    
    driver = webdriver.Edge(options=options)
    try:
        url = "https://m.oliveyoung.co.kr/m/goods/getGoodsDetail.do?goodsNo=A000000166709"
        print(f"[*] Opening mobile page: {url}")
        driver.get(url)
        time.sleep(5)
        
        # Look for review button/tab and click it
        print("[*] Finding review tab...")
        buttons = driver.find_elements(By.XPATH, "//*[contains(text(), '리뷰')]")
        for btn in buttons:
            try:
                driver.execute_script("arguments[0].click();", btn)
                print("[*] Clicked review tab!")
                time.sleep(3)
                break
            except:
                continue
                
        # Scroll down a bit
        print("[*] Scrolling down...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.5);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        # Save page source to absolute scratch path
        html = driver.page_source
        script_dir = os.path.dirname(os.path.abspath(__file__))
        out_path = os.path.join(script_dir, "mobile_page.html")
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[*] Saved HTML structure to {out_path}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
