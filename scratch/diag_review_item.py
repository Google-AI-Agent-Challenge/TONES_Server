# -*- coding: utf-8 -*-
"""
oy-review-review-item 한 개의 shadow DOM 상세 구조 덤프.
실행: python scratch/diag_review_item.py
"""
import sys, time, json, os
sys.stdout.reconfigure(encoding='utf-8')

EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
GOODS_NO = "A000000166709"
URL = f"https://m.oliveyoung.co.kr/m/goods/getGoodsDetail.do?goodsNo={GOODS_NO}"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(OUT_DIR, "diag_review_item.txt")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("=== oy-review-review-item Shadow DOM ===\n\n")

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

driver = webdriver.Edge(options=options)
try:
    driver.get(URL)
    time.sleep(6)
    driver.execute_script("document.body.style.overflow='auto'; document.documentElement.style.overflow='auto';")

    for el in driver.find_elements(By.XPATH, "//*[contains(text(), '리뷰')]"):
        try:
            txt, y = el.text.strip(), el.location.get('y', 0)
            if '리뷰' in txt and y >= 200:
                driver.execute_script("arguments[0].click();", el)
                log(f"[1] Review tab clicked: '{txt[:30]}'")
                break
        except Exception:
            continue
    time.sleep(5)

    for _ in range(8):
        driver.execute_script("window.scrollBy(0, 700);")
        time.sleep(0.8)
    time.sleep(3)

    # ── 각 oy-review-review-item 의 shadow DOM 전체 덤프 ──────────
    log("\n=== oy-review-review-item shadow DOMs ===")
    result = driver.execute_script("""
        // 모든 shadow DOM을 재귀 탐색하여 oy-review-review-item 수집
        function findAll(root, tag, depth) {
            if (!root || depth > 8) return [];
            let found = [];
            const all = root.querySelectorAll ? Array.from(root.querySelectorAll('*')) : [];
            for (const el of all) {
                if (el.tagName && el.tagName.toLowerCase() === tag) found.push(el);
                if (el.shadowRoot) found = found.concat(findAll(el.shadowRoot, tag, depth+1));
            }
            return found;
        }

        const items = findAll(document, 'oy-review-review-item', 0);
        const result = [];
        for (const item of items) {
            if (!item.shadowRoot) {
                result.push({hasRoot: false, outerHTML: item.outerHTML.substring(0, 100)});
                continue;
            }
            const sr = item.shadowRoot;
            // 모든 자식 요소와 클래스명 + 텍스트 수집
            const elements = Array.from(sr.querySelectorAll('*')).map(el => ({
                tag: el.tagName,
                cls: (el.className||'').toString().substring(0, 80),
                id:  el.id || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                style: (el.getAttribute('style') || '').substring(0, 80),
                directText: Array.from(el.childNodes)
                    .filter(n => n.nodeType === 3)
                    .map(n => n.textContent.trim()).join(' ').substring(0, 80),
                fullText: el.textContent.trim().substring(0, 60)
            }));
            result.push({hasRoot: true, shadowHTML: sr.innerHTML.substring(0, 3000), elements});
        }
        return JSON.stringify(result, null, 2);
    """)

    items = json.loads(result or "[]")
    log(f"Found {len(items)} oy-review-review-item(s)\n")

    # 첫 5개만 상세 출력
    for idx, item in enumerate(items[:5]):
        log(f"\n========== Item [{idx}] ==========")
        if not item.get('hasRoot'):
            log(f"  No shadowRoot. outerHTML: {item.get('outerHTML','')}")
            continue
        log(f"Shadow HTML preview:\n{item.get('shadowHTML','')[:1000]}")
        log(f"\nAll child elements:")
        for el in item.get('elements', [])[:30]:
            if el['cls'] or el['directText'] or el['fullText'] or el['ariaLabel']:
                log(f"  <{el['tag']}> cls='{el['cls']}' id='{el['id']}'")
                log(f"    aria='{el['ariaLabel']}' style='{el['style']}'")
                log(f"    direct='{el['directText']}'  full='{el['fullText']}'")

    log("\n=== DONE ===")
finally:
    driver.quit()
    print(f"\n[Done] → {LOG_FILE}")
