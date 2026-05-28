# -*- coding: utf-8 -*-
"""
모바일 올리브영 리뷰 섹션 DOM 구조 진단 스크립트.
실행: python scratch/diag_mobile_review.py
결과: scratch/diag_mobile_review.txt (DOM 구조 + 더보기 버튼 정보)
"""

import sys
import time
import os

sys.stdout.reconfigure(encoding='utf-8')

EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
GOODS_NO = "A000000166709"
URL = f"https://m.oliveyoung.co.kr/m/goods/getGoodsDetail.do?goodsNo={GOODS_NO}"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(OUT_DIR, "diag_mobile_review.txt")
HTML_FILE = os.path.join(OUT_DIR, "diag_mobile_review.html")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("=== Mobile Review DOM Diagnosis ===\n\n")

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

log(f"Target URL: {URL}")
log("Starting Edge driver (headless mobile)...")
driver = webdriver.Edge(options=options)
log("Driver started.\n")

try:
    # ── 1. 페이지 로드 ──────────────────────────────────────────────
    driver.get(URL)
    log("[1] Page loaded. Waiting 6s for JS render...")
    time.sleep(6)

    # ── 2. 팝업 제거 ────────────────────────────────────────────────
    driver.execute_script("""
        ['[class*="popup"]','[class*="modal"]','[class*="dimmed"]',
         '[class*="overlay"]','[class*="layer"]','[class*="banner"]'].forEach(sel => {
            document.querySelectorAll(sel).forEach(el => {
                const cls = (el.className||'').toLowerCase();
                if (!cls.includes('review') && !cls.includes('gdas'))
                    el.style.display = 'none';
            });
        });
        document.body.style.overflow = 'auto';
        document.documentElement.style.overflow = 'auto';
    """)
    time.sleep(1)

    # ── 3. 리뷰 탭 클릭 ────────────────────────────────────────────
    clicked_tab = False
    for el in driver.find_elements(By.XPATH, "//*[contains(text(), '리뷰')]"):
        try:
            txt = el.text.strip()
            y = el.location.get('y', 0)
            if '리뷰' in txt and y >= 200:
                driver.execute_script("arguments[0].click();", el)
                log(f"[2] Review tab clicked: '{txt[:30]}' (y={y})")
                clicked_tab = True
                time.sleep(3.5)
                break
        except Exception:
            continue
    if not clicked_tab:
        log("[2] Review tab NOT clicked.")

    # ── 4. 리뷰 섹션으로 스크롤 ────────────────────────────────────
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.5);")
    time.sleep(1.5)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1.5)

    # ── 5. 전체 page_source 저장 ────────────────────────────────────
    html = driver.page_source
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    log(f"[3] Full page HTML saved to: {HTML_FILE}  ({len(html):,} bytes)\n")

    # ── 6. DOM 내 '더보기' 텍스트를 가진 모든 요소 탐색 ────────────
    more_info = driver.execute_script("""
        const results = [];
        function getAncestorPath(el, depth) {
            let path = '', cur = el, d = 0;
            while (cur && d < depth) {
                const tag = cur.tagName || '';
                const cls = (cur.className || '').toString().substring(0, 60);
                const id  = cur.id ? '#' + cur.id : '';
                path = tag + id + '.' + cls + ' > ' + path;
                cur = cur.parentElement;
                d++;
            }
            return path;
        }

        document.querySelectorAll('*').forEach(el => {
            const txt = el.textContent.trim();
            if (txt === '더보기' || txt === '더 보기') {
                const rect = el.getBoundingClientRect();
                results.push({
                    tag:       el.tagName,
                    id:        el.id || '',
                    cls:       (el.className || '').toString().substring(0, 80),
                    txt:       txt,
                    visible:   el.offsetParent !== null,
                    display:   window.getComputedStyle(el).display,
                    rect:      { top: Math.round(rect.top), left: Math.round(rect.left),
                                 w: Math.round(rect.width), h: Math.round(rect.height) },
                    path:      getAncestorPath(el, 6)
                });
            }
        });
        return JSON.stringify(results, null, 2);
    """)

    log("=== All elements with text '더보기' ===")
    import json
    more_items = json.loads(more_info or "[]")
    log(f"Found {len(more_items)} element(s):\n")
    for i, item in enumerate(more_items):
        log(f"  [{i}] <{item['tag']}> id='{item['id']}' visible={item['visible']} display={item['display']}")
        log(f"       class: {item['cls']}")
        log(f"       rect : top={item['rect']['top']} w={item['rect']['w']} h={item['rect']['h']}")
        log(f"       path : {item['path'][:200]}")
        log("")

    # ── 7. 'gdas' 또는 'review' 클래스를 가진 최상위 섹션 탐색 ─────
    section_info = driver.execute_script("""
        const results = [];
        document.querySelectorAll('*').forEach(el => {
            const cls = (el.className || '').toString().toLowerCase();
            const id  = (el.id || '').toLowerCase();
            if ((cls.includes('gdas') || cls.includes('review') ||
                 id.includes('gdas')  || id.includes('review')) && el.children.length > 0) {
                results.push({
                    tag:      el.tagName,
                    id:       el.id || '',
                    cls:      (el.className || '').toString().substring(0, 100),
                    children: el.children.length,
                    html:     el.outerHTML.substring(0, 300)
                });
            }
        });
        // 중복 제거: 부모-자식 관계인 경우 자식만 남김 (children 적은 것 우선)
        return JSON.stringify(results.slice(0, 30), null, 2);
    """)

    log("\n=== Elements with 'gdas' or 'review' in class/id ===")
    sections = json.loads(section_info or "[]")
    log(f"Found {len(sections)} element(s):\n")
    for i, s in enumerate(sections[:15]):
        log(f"  [{i}] <{s['tag']}> id='{s['id']}' children={s['children']}")
        log(f"       class: {s['cls']}")
        log(f"       html preview: {s['html'][:200]}")
        log("")

    # ── 8. 현재 scrollHeight 및 document.body 구조 확인 ────────────
    scroll_info = driver.execute_script("""
        return JSON.stringify({
            scrollHeight: document.body.scrollHeight,
            scrollY:      window.scrollY,
            innerHeight:  window.innerHeight,
            totalElements: document.querySelectorAll('*').length
        });
    """)
    log(f"\n=== Page metrics ===\n{scroll_info}\n")

    log("=== DIAGNOSIS COMPLETE ===")

finally:
    driver.quit()
    log("Driver closed.")
    print(f"\n[Done] Results saved to:\n  {LOG_FILE}\n  {HTML_FILE}")
