# -*- coding: utf-8 -*-
"""
/review/api/v2/reviews/cursor 요청의 전체 파라미터(method, headers, body) 캡처.
실행: python scratch/diag_api_params.py
결과: scratch/diag_api_params.txt
"""

import sys, time, json, os
sys.stdout.reconfigure(encoding='utf-8')

EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
GOODS_NO = "A000000166709"
URL = f"https://m.oliveyoung.co.kr/m/goods/getGoodsDetail.do?goodsNo={GOODS_NO}"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(OUT_DIR, "diag_api_params.txt")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("=== Review API Full Request Capture ===\n\n")

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By

options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--window-size=375,812")
options.binary_location = EDGE_BINARY_PATH
options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")

# fetch 전체 인터셉터 (method + headers + body + response 캡처)
FULL_INTERCEPT = """
window.__reviewRequests = [];
const origFetch = window.fetch;
window.fetch = function(input, init) {
    const url   = typeof input === 'string' ? input : (input.url || '');
    const method = (init && init.method) || 'GET';
    const body  = (init && init.body)   || null;
    const hdrs  = (init && init.headers) || {};

    return origFetch.apply(this, arguments).then(res => {
        if (url.includes('/review/api/')) {
            res.clone().text().then(text => {
                window.__reviewRequests.push({
                    url, method,
                    requestHeaders: JSON.stringify(hdrs),
                    requestBody:    body ? body.toString().substring(0, 500) : null,
                    status:         res.status,
                    responseBody:   text.substring(0, 1000)
                });
            });
        }
        return res;
    });
};
"""

driver = webdriver.Edge(options=options)
try:
    driver.get(URL)
    driver.execute_script(FULL_INTERCEPT)
    log(f"[1] Page loaded + interceptor injected. Waiting 6s...")
    time.sleep(6)

    # 팝업 제거
    driver.execute_script("""
        document.body.style.overflow='auto';
        document.documentElement.style.overflow='auto';
        ['[class*="popup"]','[class*="modal"]','[class*="dimmed"]'].forEach(sel =>
            document.querySelectorAll(sel).forEach(el=>{if(!(el.className||'').includes('review'))el.style.display='none'})
        );
    """)

    # 리뷰 탭 클릭
    for el in driver.find_elements(By.XPATH, "//*[contains(text(), '리뷰')]"):
        try:
            txt, y = el.text.strip(), el.location.get('y', 0)
            if '리뷰' in txt and y >= 200:
                driver.execute_script("arguments[0].click();", el)
                log(f"[2] Review tab clicked: '{txt[:30]}'")
                break
        except Exception:
            continue

    time.sleep(4)

    # 스크롤하여 리뷰 로딩 유도
    log("[3] Scrolling to load reviews...")
    for _ in range(6):
        driver.execute_script("window.scrollBy(0, 700);")
        time.sleep(1)
    time.sleep(3)

    # 캡처된 요청 출력
    captured = driver.execute_script("return JSON.stringify(window.__reviewRequests || []);")
    reqs = json.loads(captured or "[]")
    log(f"\n=== Captured {len(reqs)} /review/api/ request(s) ===\n")

    for i, r in enumerate(reqs):
        log(f"--- Request [{i}] ---")
        log(f"  URL    : {r['url']}")
        log(f"  Method : {r['method']}")
        log(f"  Req Headers: {r['requestHeaders']}")
        log(f"  Req Body   : {r['requestBody']}")
        log(f"  Status : {r['status']}")
        log(f"  Res Body (500c): {r['responseBody'][:500]}")
        log("")

    # 현재 쿠키 목록
    cookies = driver.get_cookies()
    log(f"\n=== Session Cookies ({len(cookies)} total) ===")
    for c in cookies:
        log(f"  {c['name']}={str(c['value'])[:40]}  domain={c.get('domain','')} path={c.get('path','')}")

    log("\n=== DONE ===")

finally:
    driver.quit()
    log("Driver closed.")
    print(f"\n[Done] → {LOG_FILE}")
