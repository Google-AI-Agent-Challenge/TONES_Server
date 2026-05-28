# -*- coding: utf-8 -*-
"""
Olive Young Review shadow DOM dumper to inspect exact pagination selectors
"""

import os
import sys
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By

EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
goods_no = "A000000166709" # Skinfood pads integrated page
url = f"https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo={goods_no}"

print("Connecting to Edge driver...")
options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
options.binary_location = EDGE_BINARY_PATH
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Edge(options=options)
try:
    print(f"Opening page: {url}")
    driver.get(url)
    time.sleep(5)
    
    # Scroll to reviews tab area and click reviews tab
    print("Scrolling to tab...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3);")
    time.sleep(1.5)
    
    buttons = driver.find_elements(By.TAG_NAME, "button")
    for btn in buttons:
        txt = btn.text
        if "리뷰&셔터" in txt or "리뷰 " in txt:
            driver.execute_script("arguments[0].click();", btn)
            print(f"Reviews tab clicked!")
            break
            
    time.sleep(4)
    
    # Scroll into the reviews list area
    print("Scrolling down to reviews list container...")
    driver.execute_script("""
        let el = document.querySelector('oy-review-review-in-product');
        if (el) {
            el.scrollIntoView({behavior: 'instant', block: 'center'});
        }
    """)
    time.sleep(2)
    
    driver.execute_script("window.scrollBy(0, 500);")
    time.sleep(2)
    
    # Dump HTML inside root2
    print("Dumping reviewList shadow DOM innerHTML...")
    dump_script = """
    let inProd = document.querySelector('oy-review-review-in-product');
    if (!inProd) return "Error: oy-review-review-in-product not found";
    let root1 = inProd.shadowRoot;
    if (!root1) return "Error: oy-review-review-in-product shadowRoot not found";
    
    let listProvider = root1.querySelector('oy-review-review-list-provider');
    if (!listProvider) return "Error: oy-review-review-list-provider not found";
    let reviewList = listProvider.querySelector('oy-review-review-list');
    if (!reviewList) return "Error: oy-review-review-list not found";
    let root2 = reviewList.shadowRoot;
    if (!root2) return "Error: oy-review-review-list shadowRoot not found";
    
    return root2.innerHTML;
    """
    
    html_content = driver.execute_script(dump_script)
    
    output_path = "scratch/reviews_dom.html"
    os.makedirs("scratch", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"✅ Success! HTML dumped to {output_path} ({len(html_content)} bytes)")
    
finally:
    driver.quit()
