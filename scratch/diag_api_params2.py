# -*- coding: utf-8 -*-
"""
CDP(Page.addScriptToEvaluateOnNewDocument)로 페이지 로드 전에 인터셉터 주입.
fetch 요청의 method/body/headers/response를 완전하게 캡처.
실행: python scratch/diag_api_params2.py
"""
import sys, time, json, os
sys.stdout.reconfigure(encoding='utf-8')

EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
GOODS_NO = "A000000166709"
URL = f"https://m.oliveyoung.co.kr/m/goods/getGoodsDetail.do?goodsNo={GOODS_NO}"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(OUT_DIR, "diag_api_params2.txt")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("=== Review API Params Capture (CDP) ===\n\n")

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

INTERCEPT_JS = """
window.__apiLog = [];
const _origFetch = window.fetch;
window.fetch = async function(input, init) {
    const url    = typeof input === 'string' ? input : (input && input.url) || '';
    const method = (init && init.method) || (input && input.method) || 'GET';
    let   body   = (init && init.body)   || (input && input.body)   || null;
    const hdrs   = {};
    if (init && init.headers) {
        try {
            const h = new Headers(init.headers);
            h.forEach((v,k) => { hdrs[k] = v; });
        } catch(e) {
            try { Object.assign(hdrs, init.headers); } catch(e2) {}
        }
    }
    if (body && typeof body !== 'string') {
        try { body = await body.text ? body.text() : JSON.stringify(body); } catch(e) { body = String(body); }
    }

    const res = await _origFetch.apply(this, arguments);
    if (url.includes('/review/api/')) {
        try {
            const text = await res.clone().text();
            window.__apiLog.push({
                url, method,
                requestHeaders: JSON.stringify(hdrs),
                requestBody: body,
                status: res.status,
                responseBody: text.substring(0, 2000)
            });
        } catch(e) {}
    }
    return res;
};
"""

driver = webdriver.Edge(options=options)
try:
    # 페이지 로드 전에 인터셉터 주입 (CDP)
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': INTERCEPT_JS})
    log("[1] CDP interceptor injected (pre-load).")

    driver.get(URL)
    log(f"[2] Page loaded. Waiting 7s...")
    time.sleep(7)

    # 팝업 제거
    driver.execute_script("""
        document.body.style.overflow='auto';
        document.documentElement.style.overflow='auto';
        ['[class*="popup"]','[class*="modal"]','[class*="dimmed"]'].forEach(sel =>
            document.querySelectorAll(sel).forEach(el=>{if(!(el.className||'').includes('review'))el.style.display='none';})
        );
    """)
    time.sleep(0.5)

    # 리뷰 탭 클릭
    for el in driver.find_elements(By.XPATH, "//*[contains(text(), '리뷰')]"):
        try:
            txt, y = el.text.strip(), el.location.get('y', 0)
            if '리뷰' in txt and y >= 200:
                driver.execute_script("arguments[0].click();", el)
                log(f"[3] Clicked review tab: '{txt[:30]}'")
                break
        except Exception:
            continue

    time.sleep(5)

    # 스크롤 → 더 많은 리뷰 로드
    log("[4] Scrolling...")
    for _ in range(5):
        driver.execute_script("window.scrollBy(0, 700);")
        time.sleep(1.2)
    time.sleep(3)

    # 캡처된 요청 출력
    raw = driver.execute_script("return JSON.stringify(window.__apiLog || []);")
    reqs = json.loads(raw or "[]")
    log(f"\n=== Captured {len(reqs)} /review/api/ request(s) ===\n")

    for i, r in enumerate(reqs):
        log(f"[{i}] ─────────────────────────────────────────")
        log(f"  URL    : {r['url']}")
        log(f"  Method : {r['method']}")
        log(f"  ReqHdrs: {r['requestHeaders']}")
        log(f"  ReqBody: {r['requestBody']}")
        log(f"  Status : {r['status']}")
        log(f"  ResBody: {r['responseBody']}")
        log("")

    # 쿠키
    cookies = driver.get_cookies()
    log(f"\n=== Cookies ({len(cookies)}) ===")
    for c in cookies:
        log(f"  {c['name']}={str(c['value'])[:60]}  domain={c.get('domain','')}")

    log("\n=== DONE ===")
finally:
    driver.quit()
    print(f"\n[Done] → {LOG_FILE}")
