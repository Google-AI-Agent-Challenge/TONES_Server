# -*- coding: utf-8 -*-
"""
Shadow DOM 내부 구조 + 네트워크 요청으로 리뷰 API 엔드포인트 확인.
실행: python scratch/diag_shadow_and_api.py
결과: scratch/diag_shadow_api.txt
"""

import sys, time, json, os
sys.stdout.reconfigure(encoding='utf-8')

EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
GOODS_NO = "A000000166709"
URL = f"https://m.oliveyoung.co.kr/m/goods/getGoodsDetail.do?goodsNo={GOODS_NO}"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(OUT_DIR, "diag_shadow_api.txt")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("=== Shadow DOM + API Endpoint Diagnosis ===\n\n")

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

# 네트워크 요청 가로채기용 Performance Logging 활성화
from selenium.webdriver.edge.service import Service
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Edge(options=options)

# ── XHR 인터셉터 주입 (페이지 로드 전에 실행) ──────────────────────────
INTERCEPT_SCRIPT = """
window.__capturedRequests = [];
const origOpen = XMLHttpRequest.prototype.open;
XMLHttpRequest.prototype.open = function(method, url) {
    this.__url = url;
    origOpen.apply(this, arguments);
};
const origSend = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.send = function(body) {
    this.addEventListener('load', function() {
        if (this.__url && (
            this.__url.includes('review') ||
            this.__url.includes('Review') ||
            this.__url.includes('gdas') ||
            this.__url.includes('comment')
        )) {
            window.__capturedRequests.push({
                url: this.__url,
                status: this.status,
                responsePreview: this.responseText.substring(0, 500)
            });
        }
    });
    origSend.apply(this, arguments);
};

const origFetch = window.fetch;
window.fetch = function(input, init) {
    const url = typeof input === 'string' ? input : input.url;
    return origFetch.apply(this, arguments).then(res => {
        if (url && (url.includes('review') || url.includes('Review') ||
                    url.includes('gdas') || url.includes('comment'))) {
            res.clone().text().then(text => {
                window.__capturedRequests.push({
                    url: url,
                    status: res.status,
                    responsePreview: text.substring(0, 500)
                });
            });
        }
        return res;
    });
};
"""

try:
    driver.get(URL)

    # XHR 인터셉터 주입
    driver.execute_script(INTERCEPT_SCRIPT)
    log(f"[1] XHR interceptor injected. Waiting 6s...")
    time.sleep(6)

    # 팝업 제거
    driver.execute_script("""
        document.body.style.overflow = 'auto';
        document.documentElement.style.overflow = 'auto';
        ['[class*="popup"]','[class*="modal"]','[class*="dimmed"]'].forEach(sel =>
            document.querySelectorAll(sel).forEach(el => {
                if (!(el.className||'').includes('review')) el.style.display='none';
            })
        );
    """)

    # 리뷰 탭 클릭
    for el in driver.find_elements(By.XPATH, "//*[contains(text(), '리뷰')]"):
        try:
            txt, y = el.text.strip(), el.location.get('y', 0)
            if '리뷰' in txt and y >= 200:
                driver.execute_script("arguments[0].click();", el)
                log(f"[2] Clicked review tab: '{txt[:30]}' (y={y})")
                break
        except Exception:
            continue

    # 더보기 아이콘 클릭 시도 (ReviewArea_icon-more__myhwK)
    try:
        more_icon = driver.find_element(By.CSS_SELECTOR, "[class*='icon-more']")
        driver.execute_script("arguments[0].click();", more_icon)
        log("[3] Clicked ReviewArea icon-more button")
    except Exception:
        log("[3] ReviewArea icon-more not found, skipping")

    time.sleep(3)

    # 충분히 스크롤하여 컴포넌트 완전 렌더링 유도
    log("[4] Scrolling to force full render...")
    for i in range(8):
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(0.8)
    time.sleep(3)

    # ── Shadow DOM 덤프 ──────────────────────────────────────────────
    log("\n=== Shadow DOM of oy-review-review-in-product ===")
    shadow_result = driver.execute_script("""
        const comp = document.querySelector('oy-review-review-in-product');
        if (!comp) return {error: 'component not found'};

        function dumpShadow(root, depth) {
            if (!root || depth > 4) return {childCount: 0, html: '', nestedShadows: []};
            const all = Array.from(root.querySelectorAll('*'));
            const nested = [];
            for (const el of all) {
                if (el.shadowRoot) {
                    nested.push({
                        tag: el.tagName,
                        cls: (el.className||'').substring(0, 60),
                        shadowHTML: el.shadowRoot.innerHTML.substring(0, 1000),
                        childCount: el.shadowRoot.querySelectorAll('*').length
                    });
                }
            }
            return {
                childCount: all.length,
                html: root.innerHTML.substring(0, 2000),
                nestedShadows: nested
            };
        }

        if (!comp.shadowRoot) {
            return {
                error: 'no shadowRoot on oy-review-review-in-product',
                innerHTML: comp.innerHTML.substring(0, 500),
                childCount: comp.querySelectorAll('*').length
            };
        }

        return dumpShadow(comp.shadowRoot, 0);
    """)
    log(json.dumps(shadow_result, ensure_ascii=False, indent=2)[:4000])

    # ── 전체 Shadow DOM 재귀 탐색 (더보기 버튼 찾기) ────────────────
    log("\n=== Searching for '더보기' inside ALL Shadow DOMs ===")
    more_btn_result = driver.execute_script("""
        const results = [];
        function traverse(root, depth) {
            if (!root || depth > 6) return;
            const all = root.querySelectorAll ? Array.from(root.querySelectorAll('*')) : [];
            for (const el of all) {
                const txt = el.textContent.trim();
                if (txt === '더보기' || txt === '더 보기' || txt === '리뷰 더보기') {
                    let path = '', cur = el, d = 0;
                    while (cur && d < 5) {
                        path = (cur.tagName||'') + '.' + (cur.className||'').substring(0,30) + ' > ' + path;
                        cur = cur.parentElement || cur.parentNode;
                        d++;
                    }
                    results.push({
                        tag: el.tagName, cls: (el.className||'').substring(0,80),
                        txt: txt, visible: el.offsetParent !== null, path: path
                    });
                }
                if (el.shadowRoot) traverse(el.shadowRoot, depth + 1);
            }
        }
        traverse(document, 0);
        return JSON.stringify(results, null, 2);
    """)
    items = json.loads(more_btn_result or "[]")
    log(f"Found {len(items)} '더보기' elements (including Shadow DOM):")
    for i, item in enumerate(items):
        log(f"  [{i}] <{item['tag']}> visible={item['visible']}")
        log(f"       cls: {item['cls']}")
        log(f"       txt: {item['txt']}")
        log(f"       path: {item['path'][:200]}")

    # ── 리뷰 콘텐츠 탐색 (Shadow DOM 포함) ──────────────────────────
    log("\n=== Searching for review text content in Shadow DOM ===")
    review_content_result = driver.execute_script("""
        const results = [];
        function traverse(root, depth, inShadow) {
            if (!root || depth > 6) return;
            const all = root.querySelectorAll ? Array.from(root.querySelectorAll('*')) : [];
            for (const el of all) {
                const cls = (el.className||'').toString().toLowerCase();
                const id  = (el.id||'').toLowerCase();
                if (cls.includes('review') || cls.includes('gdas') ||
                    id.includes('review')  || id.includes('gdas')) {
                    const txt = el.textContent.trim().substring(0, 80);
                    if (txt.length > 5) {
                        results.push({
                            inShadow, tag: el.tagName,
                            cls: (el.className||'').toString().substring(0, 80),
                            txt: txt, childCount: el.children.length
                        });
                    }
                }
                if (el.shadowRoot) traverse(el.shadowRoot, depth + 1, true);
            }
        }
        traverse(document, 0, false);
        return JSON.stringify(results.slice(0, 40), null, 2);
    """)
    review_items = json.loads(review_content_result or "[]")
    log(f"Found {len(review_items)} review-related elements (incl. Shadow DOM):")
    for i, item in enumerate(review_items[:20]):
        shadow_mark = "[SHADOW]" if item['inShadow'] else "[DOM]"
        log(f"  [{i}] {shadow_mark} <{item['tag']}> cls={item['cls']}")
        log(f"       txt: {item['txt']}")

    # ── 캡처된 네트워크 요청 ─────────────────────────────────────────
    log("\n=== Captured XHR/Fetch review-related requests ===")
    captured = driver.execute_script("return JSON.stringify(window.__capturedRequests || []);")
    reqs = json.loads(captured or "[]")
    log(f"Found {len(reqs)} captured request(s):")
    for i, r in enumerate(reqs):
        log(f"  [{i}] {r.get('url','')}")
        log(f"       status={r.get('status','')}  preview={r.get('responsePreview','')[:200]}")

    # ── Performance API로 모든 리소스 URL 스캔 ───────────────────────
    log("\n=== All resource URLs containing 'review' or 'gdas' (Performance API) ===")
    perf_urls = driver.execute_script("""
        return performance.getEntriesByType('resource')
            .map(e => e.name)
            .filter(u => u.includes('review') || u.includes('Review') ||
                         u.includes('gdas') || u.includes('comment'));
    """)
    log(f"Found {len(perf_urls)} matching URLs:")
    for u in perf_urls:
        log(f"  {u}")

    log("\n=== DIAGNOSIS COMPLETE ===")

finally:
    driver.quit()
    log("Driver closed.")
    print(f"\n[Done] → {LOG_FILE}")
