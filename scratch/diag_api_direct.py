# -*- coding: utf-8 -*-
"""
/review/api/v2/reviews/cursor 를 curl_cffi로 직접 호출하여
올바른 파라미터 조합과 응답 구조를 확인.
실행: python scratch/diag_api_direct.py
"""
import sys, time, json, os
sys.stdout.reconfigure(encoding='utf-8')

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(OUT_DIR, "diag_api_direct.txt")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("=== Direct API Call Test ===\n\n")

# ── Selenium으로 실제 쿠키 & Referer 확보 ──────────────────────────
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from curl_cffi import requests as cffi_requests

EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
GOODS_NO = "A000000166709"
MOBILE_URL = f"https://m.oliveyoung.co.kr/m/goods/getGoodsDetail.do?goodsNo={GOODS_NO}"
API_BASE   = "https://m.oliveyoung.co.kr/review/api/v2/reviews"

options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--window-size=375,812")
options.binary_location = EDGE_BINARY_PATH
options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")

log("1) Getting session cookies via Selenium...")
driver = webdriver.Edge(options=options)
try:
    driver.get(MOBILE_URL)
    time.sleep(6)

    # 리뷰 탭 클릭 → 웹 컴포넌트 초기화 + 쿠키 갱신
    for el in driver.find_elements(By.XPATH, "//*[contains(text(), '리뷰')]"):
        try:
            txt, y = el.text.strip(), el.location.get('y', 0)
            if '리뷰' in txt and y >= 200:
                driver.execute_script("arguments[0].click();", el)
                log(f"   Clicked: '{txt[:30]}'")
                break
        except Exception:
            continue
    time.sleep(3)

    raw_cookies = driver.get_cookies()
    referer     = driver.current_url
finally:
    driver.quit()

# curl_cffi용 쿠키 딕셔너리
cookies = {c['name']: c['value'] for c in raw_cookies}
log(f"   Got {len(cookies)} cookies from Selenium.\n")

UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"

base_headers = {
    "User-Agent": UA,
    "Referer": referer,
    "Origin": "https://m.oliveyoung.co.kr",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

def try_call(label, method, url, params=None, json_body=None, extra_headers=None):
    hdrs = {**base_headers, **(extra_headers or {})}
    try:
        if method == "GET":
            r = cffi_requests.get(url, params=params, headers=hdrs, cookies=cookies,
                                  impersonate="chrome110", timeout=20)
        else:
            r = cffi_requests.post(url, params=params, json=json_body,
                                   headers={**hdrs, "Content-Type": "application/json"},
                                   cookies=cookies, impersonate="chrome110", timeout=20)
        log(f"[{label}] {method} {url}")
        log(f"  params/body : {params or json_body}")
        log(f"  status      : {r.status_code}")
        try:
            parsed = r.json()
            log(f"  response    : {json.dumps(parsed, ensure_ascii=False)[:800]}")
            return parsed
        except Exception:
            log(f"  raw (500c)  : {r.text[:500]}")
            return None
    except Exception as e:
        log(f"[{label}] ERROR: {e}")
        return None
    finally:
        log("")

# ── 시도 A: GET cursor ──────────────────────────────────────────
log("=== Test A: GET /cursor (goodsNo only) ===")
try_call("A1", "GET", f"{API_BASE}/cursor",
         params={"goodsNo": GOODS_NO})

try_call("A2", "GET", f"{API_BASE}/cursor",
         params={"goodsNo": GOODS_NO, "size": 10})

try_call("A3", "GET", f"{API_BASE}/cursor",
         params={"goodsNo": GOODS_NO, "size": 10, "sortType": "RECENT"})

try_call("A4", "GET", f"{API_BASE}/cursor",
         params={"goodsNo": GOODS_NO, "pageSize": 10, "deviceType": "mobile"})

# ── 시도 B: POST cursor ──────────────────────────────────────────
log("=== Test B: POST /cursor ===")
try_call("B1", "POST", f"{API_BASE}/cursor",
         json_body={"goodsNo": GOODS_NO})

try_call("B2", "POST", f"{API_BASE}/cursor",
         json_body={"goodsNo": GOODS_NO, "size": 10, "sortType": "RECENT", "deviceType": "mobile"})

try_call("B3", "POST", f"{API_BASE}/cursor",
         json_body={"goodsNo": GOODS_NO, "cursor": None, "size": 10})

# ── 시도 C: GET /cursor with goodsNo in path ─────────────────────
log("=== Test C: GET /cursor with goodsNo in path ===")
try_call("C1", "GET", f"{API_BASE}/{GOODS_NO}/cursor",
         params={"size": 10})

try_call("C2", "GET", f"{API_BASE}/{GOODS_NO}/cursor",
         params={"size": 10, "sortType": "RECENT", "deviceType": "mobile"})

# ── 시도 D: stats & options ──────────────────────────────────────
log("=== Test D: Other confirmed endpoints ===")
try_call("D1", "GET", f"{API_BASE}/{GOODS_NO}/stats")
try_call("D2", "GET", f"{API_BASE}/options/{GOODS_NO}/count")

log("\n=== ALL TESTS DONE ===")
print(f"\n[Done] → {LOG_FILE}")
