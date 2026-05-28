# -*- coding: utf-8 -*-
"""
최소화된 페이지네이션 진단 스크립트.
결과를 파일에 직접 써서 agent가 읽을 수 있도록 함.
python scratch/diag_pagination.py
"""

import sys
import time
import json

# stdout을 파일로 직접 리다이렉트
LOG_FILE = r"d:\대외 활동 자료\Contest\Google AI Agent Challenge\Project\WooYeonChoiYeonWoo_Server\scratch\diag_output.txt"

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

# 기존 로그 초기화
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("=== Pagination Diagnosis ===\n")

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By

EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
goods_no = "A000000166709"
url = f"https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo={goods_no}"

log(f"Target: {url}")

options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.binary_location = EDGE_BINARY_PATH
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

log("Starting Edge driver...")
driver = webdriver.Edge(options=options)
log("Edge driver started!")

try:
    driver.get(url)
    log("Page loaded, waiting 6s...")
    time.sleep(6)

    # 리뷰 탭 클릭
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3);")
    time.sleep(1.5)
    buttons = driver.find_elements(By.TAG_NAME, "button")
    for btn in buttons:
        txt = btn.text
        if "리뷰&셔터" in txt or "리뷰 " in txt:
            driver.execute_script("arguments[0].click();", btn)
            log(f"Reviews tab clicked: {txt}")
            break
    time.sleep(4)

    # 리뷰 컨테이너로 스크롤
    driver.execute_script("""
        let el = document.querySelector('oy-review-review-in-product');
        if (el) el.scrollIntoView({behavior: 'instant', block: 'center'});
    """)
    time.sleep(2)
    driver.execute_script("window.scrollBy(0, 600);")
    time.sleep(2)

    # === 핵심 진단: "2" 텍스트를 가진 모든 요소 찾기 ===
    find_script = """
    let allEls = [];
    function collect(root) {
        if (!root) return;
        let els = Array.from(root.querySelectorAll('*'));
        for (let el of els) {
            allEls.push(el);
            if (el.shadowRoot) collect(el.shadowRoot);
        }
    }
    collect(document);

    let results = [];
    for (let el of allEls) {
        let directText = Array.from(el.childNodes)
            .filter(n => n.nodeType === Node.TEXT_NODE)
            .map(n => n.textContent.trim())
            .join('');
        let fullText = el.textContent.trim();
        
        if (directText === '2' || fullText === '2') {
            let path = '';
            let cur = el;
            let d = 0;
            while (cur && d < 12) {
                path += (cur.tagName||'') + '.' + (cur.className||'').substring(0,30) + ' > ';
                cur = cur.parentNode || cur.host;
                d++;
            }
            results.push({
                tag: el.tagName,
                cls: (el.className||'').substring(0,50),
                directText: directText,
                fullText: fullText.substring(0,40),
                path: path.substring(0, 300)
            });
        }
    }
    return JSON.stringify(results, null, 2);
    """
    
    log("\n=== Finding all elements with text '2' on Page 1 ===")
    result = driver.execute_script(find_script)
    data = json.loads(result or "[]")
    log(f"Found {len(data)} elements with text '2':")
    for i, item in enumerate(data):
        log(f"  [{i}] tag={item['tag']} cls={item['cls']}")
        log(f"       directText='{item['directText']}' fullText='{item['fullText']}'")
        log(f"       path={item['path'][:200]}")

    # "2" 클릭 시도 (첫 번째 후보)
    log("\n=== Clicking page 2 ===")
    click_script = """
    let allEls = [];
    function collect(root) {
        if (!root) return;
        let els = Array.from(root.querySelectorAll('*'));
        for (let el of els) {
            allEls.push(el);
            if (el.shadowRoot) collect(el.shadowRoot);
        }
    }
    collect(document);
    
    for (let el of allEls) {
        let directText = Array.from(el.childNodes)
            .filter(n => n.nodeType === Node.TEXT_NODE)
            .map(n => n.textContent.trim())
            .join('');
        if (directText === '2') {
            el.click();
            return 'clicked: ' + el.tagName + '.' + (el.className||'');
        }
    }
    return 'NOT FOUND';
    """
    result = driver.execute_script(click_script)
    log(f"Click result: {result}")
    time.sleep(3.5)

    # 페이지 이동 후 스크롤
    driver.execute_script("""
        let el = document.querySelector('oy-review-review-in-product');
        if (el) el.scrollIntoView({behavior: 'instant', block: 'end'});
    """)
    time.sleep(1.5)
    driver.execute_script("window.scrollBy(0, 400);")
    time.sleep(1.5)

    # === 핵심 진단: Page 2에서 "3" 텍스트를 가진 모든 요소 찾기 ===
    find3_script = find_script.replace("=== '2'", "=== '3'").replace("directText === '2' || fullText === '2'", "directText === '3' || fullText === '3'")
    
    log("\n=== Finding all elements with text '3' on Page 2 ===")
    result3 = driver.execute_script(find3_script)
    data3 = json.loads(result3 or "[]")
    log(f"Found {len(data3)} elements with text '3':")
    for i, item in enumerate(data3):
        log(f"  [{i}] tag={item['tag']} cls={item['cls']}")
        log(f"       directText='{item['directText']}' fullText='{item['fullText']}'")
        log(f"       path={item['path'][:200]}")
    
    # 전체 shadow DOM 크기도 체크
    count_script = """
    let allEls = [];
    function collect(root) {
        if (!root) return;
        let els = Array.from(root.querySelectorAll('*'));
        for (let el of els) {
            allEls.push(el);
            if (el.shadowRoot) collect(el.shadowRoot);
        }
    }
    collect(document);
    return allEls.length;
    """
    total = driver.execute_script(count_script)
    log(f"\n=== Total DOM elements scanned: {total} ===")

    log("\n=== DIAGNOSIS COMPLETE ===")

finally:
    driver.quit()
    log("Driver closed.")
