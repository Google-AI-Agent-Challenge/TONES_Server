# -*- coding: utf-8 -*-
"""
oy-review-review-list Shadow DOM 전체 구조 + 더보기 버튼 덤프.
실행: python scratch/diag_shadow_full.py
"""
import sys, time, json, os
sys.stdout.reconfigure(encoding='utf-8')

EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
GOODS_NO = "A000000166709"
URL = f"https://m.oliveyoung.co.kr/m/goods/getGoodsDetail.do?goodsNo={GOODS_NO}"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(OUT_DIR, "diag_shadow_full.txt")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("=== Shadow DOM Full Dump ===\n\n")

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

    driver.execute_script("""
        document.body.style.overflow='auto';
        document.documentElement.style.overflow='auto';
        ['[class*="popup"]','[class*="modal"]','[class*="dimmed"]'].forEach(s=>
            document.querySelectorAll(s).forEach(e=>{if(!(e.className||'').includes('review'))e.style.display='none';})
        );
    """)

    # 리뷰 탭 클릭
    for el in driver.find_elements(By.XPATH, "//*[contains(text(), '리뷰')]"):
        try:
            txt, y = el.text.strip(), el.location.get('y', 0)
            if '리뷰' in txt and y >= 200:
                driver.execute_script("arguments[0].click();", el)
                log(f"[1] Clicked review tab: '{txt[:30]}'")
                break
        except Exception:
            continue
    time.sleep(5)

    # 스크롤하여 리뷰 완전 로드
    log("[2] Scrolling to load review list...")
    for _ in range(8):
        driver.execute_script("window.scrollBy(0, 700);")
        time.sleep(0.8)
    time.sleep(3)

    # ── oy-review-review-list Shadow DOM 전체 덤프 ─────────────────
    log("\n=== oy-review-review-list Shadow DOM (full HTML) ===")
    shadow_html = driver.execute_script("""
        function findDeep(root, tag) {
            if (!root) return null;
            let found = root.querySelector ? root.querySelector(tag) : null;
            if (found) return found;
            let all = root.querySelectorAll ? Array.from(root.querySelectorAll('*')) : [];
            for (let el of all) {
                if (el.shadowRoot) {
                    let r = findDeep(el.shadowRoot, tag);
                    if (r) return r;
                }
            }
            return null;
        }
        const comp = findDeep(document, 'oy-review-review-list');
        if (!comp) return 'NOT FOUND: oy-review-review-list';
        if (!comp.shadowRoot) return 'NO SHADOW ROOT';
        return comp.shadowRoot.innerHTML;
    """)
    with open(os.path.join(OUT_DIR, "shadow_review_list.html"), "w", encoding="utf-8") as f:
        f.write(shadow_html or "")
    log(f"Saved shadow DOM ({len(shadow_html or '')} bytes) to shadow_review_list.html")
    log(f"Preview (2000c):\n{(shadow_html or '')[:2000]}")

    # ── Shadow DOM 내 review-item 구조 ────────────────────────────
    log("\n=== Review items in Shadow DOM ===")
    review_items = driver.execute_script("""
        function findDeep(root, tag) {
            if (!root) return null;
            let found = root.querySelector ? root.querySelector(tag) : null;
            if (found) return found;
            let all = root.querySelectorAll ? Array.from(root.querySelectorAll('*')) : [];
            for (let el of all) {
                if (el.shadowRoot) {
                    let r = findDeep(el.shadowRoot, tag);
                    if (r) return r;
                }
            }
            return null;
        }
        const comp = findDeep(document, 'oy-review-review-list');
        if (!comp || !comp.shadowRoot) return [];

        const items = Array.from(comp.shadowRoot.querySelectorAll('[class*="review-item"], .review-item'));
        return items.map(item => ({
            outerHTML: item.outerHTML.substring(0, 600),
            classes:   item.className,
            childCount: item.children.length
        }));
    """)
    log(f"Found {len(review_items)} review-item(s) in shadow DOM:")
    for i, item in enumerate(review_items[:5]):
        log(f"\n  [{i}] classes={item['classes']} children={item['childCount']}")
        log(f"       HTML: {item['outerHTML'][:400]}")

    # ── "더보기" 버튼 in shadow DOM ────────────────────────────────
    log("\n=== 더보기 / next buttons inside ALL shadow DOMs ===")
    more_btns = driver.execute_script("""
        const results = [];
        function traverse(root, depth) {
            if (!root || depth > 8) return;
            const all = root.querySelectorAll ? Array.from(root.querySelectorAll('*')) : [];
            for (const el of all) {
                const txt = el.textContent.trim();
                const cls = (el.className||'').toString().toLowerCase();
                if (txt === '더보기' || txt === '더 보기' || txt === '다음' ||
                    cls.includes('more') || cls.includes('next') || cls.includes('load')) {
                    let path = '', cur = el, d = 0;
                    while (cur && d < 5) {
                        path = (cur.tagName||'') + '.' + (cur.className||'').toString().substring(0,25) + ' > ' + path;
                        cur = cur.parentElement || cur.parentNode;
                        d++;
                    }
                    results.push({
                        tag: el.tagName, txt: txt.substring(0,30), cls: (el.className||'').toString().substring(0,80),
                        visible: el.offsetParent !== null,
                        html: el.outerHTML.substring(0,200),
                        path: path.substring(0, 200)
                    });
                }
                if (el.shadowRoot) traverse(el.shadowRoot, depth + 1);
            }
        }
        traverse(document, 0);
        return JSON.stringify(results, null, 2);
    """)
    btns = json.loads(more_btns or "[]")
    log(f"Found {len(btns)} candidate elements:")
    for i, b in enumerate(btns):
        log(f"\n  [{i}] <{b['tag']}> visible={b['visible']} txt='{b['txt']}'")
        log(f"       cls : {b['cls']}")
        log(f"       path: {b['path']}")
        log(f"       html: {b['html'][:150]}")

    # ── 전체 Shadow DOM 텍스트 추출 (리뷰 콘텐츠) ─────────────────
    log("\n=== All review content-container texts in shadow DOM ===")
    contents = driver.execute_script("""
        const results = [];
        function traverse(root, depth) {
            if (!root || depth > 8) return;
            const all = root.querySelectorAll ? Array.from(root.querySelectorAll('*')) : [];
            for (const el of all) {
                const cls = (el.className||'').toString();
                if (cls.includes('review-content') || cls.includes('review-item')) {
                    results.push({
                        cls: cls.substring(0,60),
                        txt: el.textContent.trim().substring(0,150)
                    });
                }
                if (el.shadowRoot) traverse(el.shadowRoot, depth + 1);
            }
        }
        traverse(document, 0);
        return JSON.stringify(results.slice(0, 30), null, 2);
    """)
    items2 = json.loads(contents or "[]")
    log(f"Found {len(items2)} review content elements:")
    for i, c in enumerate(items2[:15]):
        log(f"  [{i}] cls={c['cls']}")
        log(f"       txt: {c['txt']}")

    log("\n=== DONE ===")
finally:
    driver.quit()
    print(f"\n[Done] → {LOG_FILE}")
