# -*- coding: utf-8 -*-
"""
수정된 페이지네이션 진단 스크립트 v2.
- 리뷰 탭 클릭 후 충분히 스크롤 (swiper 제외된 진짜 pagination 찾기)
python scratch/diag_pagination_v2.py
"""

import sys, time, json

LOG_FILE = r"d:\대외 활동 자료\Contest\Google AI Agent Challenge\Project\WooYeonChoiYeonWoo_Server\scratch\diag_output_v2.txt"

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("=== Pagination Diagnosis v2 ===\n")

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By

EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
goods_no = "A000000166709"
url = f"https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo={goods_no}"

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

FIND_SCRIPT = """
const TARGET = arguments[0];
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

function getPath(el) {
    let path = '';
    let cur = el, d = 0;
    while (cur && d < 12) {
        path += (cur.tagName||'') + '.' + (cur.className||'').substring(0,30) + ' > ';
        cur = cur.parentNode || cur.host;
        d++;
    }
    return path.substring(0, 300);
}

let results = [];
for (let el of allEls) {
    let directText = Array.from(el.childNodes)
        .filter(n => n.nodeType === Node.TEXT_NODE)
        .map(n => n.textContent.trim()).join('');
    let fullText = el.textContent.trim();
    if (directText === TARGET || fullText === TARGET) {
        let path = getPath(el);
        let isSwiper = path.includes('swiper') || path.includes('carousel') || 
                       path.includes('visual') || path.includes('slider');
        results.push({
            tag: el.tagName,
            cls: (el.className||'').substring(0,60),
            directText, fullText: fullText.substring(0,40),
            isSwiper, path
        });
    }
}
return JSON.stringify({total: allEls.length, results}, null, 2);
"""

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
    time.sleep(3.5)

    # ★ 핵심: 충분히 스크롤해서 pagination 컴포넌트 마운트
    log("Scrolling down to force oy-review-pagination to mount...")
    for i in range(5):
        driver.execute_script("window.scrollBy(0, 600);")
        time.sleep(0.7)
        log(f"  scroll step {i+1}/5")
    time.sleep(2.0)

    # DOM 크기 및 "2" 찾기
    log("\n=== Finding '2' after deep scroll ===")
    result = driver.execute_script(FIND_SCRIPT, "2")
    data = json.loads(result)
    log(f"Total DOM elements: {data['total']}")
    log(f"Elements with text '2': {len(data['results'])}")
    for i, item in enumerate(data['results']):
        log(f"  [{i}] tag={item['tag']} isSwiper={item['isSwiper']}")
        log(f"       cls={item['cls']}")
        log(f"       path={item['path'][:250]}")

    # 가장 적합한 "2" 클릭 (swiper 제외)
    log("\n=== Clicking best '2' (non-swiper) ===")
    click_script = """
    const TARGET = '2';
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
    
    function getPath(el) {
        let path = '', cur = el, d = 0;
        while (cur && d < 12) {
            path += (cur.tagName||'') + '.' + (cur.className||'').substring(0,20) + ' > ';
            cur = cur.parentNode || cur.host;
            d++;
        }
        return path.toLowerCase();
    }
    
    let best = null, bestScore = -1;
    for (let el of allEls) {
        let directText = Array.from(el.childNodes)
            .filter(n => n.nodeType === Node.TEXT_NODE)
            .map(n => n.textContent.trim()).join('');
        if (directText === TARGET || el.textContent.trim() === TARGET) {
            let path = getPath(el);
            if (path.includes('swiper') || path.includes('carousel') || path.includes('visual')) continue;
            let score = 0;
            if (path.includes('pagination') && path.includes('review')) score += 40;
            if (path.includes('oy-review')) score += 30;
            if (path.includes('pagination')) score += 20;
            if (path.includes('review')) score += 15;
            if (best === null || score > bestScore) {
                best = el;
                bestScore = score;
            }
        }
    }
    
    if (best) {
        best.click();
        return 'clicked score=' + bestScore + ' tag=' + best.tagName + ' cls=' + (best.className||'');
    }
    return 'NOT FOUND';
    """
    result2 = driver.execute_script(click_script)
    log(f"Click result: {result2}")
    time.sleep(3.5)

    # 페이지 이동 후 스크롤
    driver.execute_script("""
        let el = document.querySelector('oy-review-review-in-product');
        if (el) el.scrollIntoView({behavior: 'instant', block: 'start'});
    """)
    time.sleep(1.0)
    driver.execute_script("window.scrollBy(0, 800);")
    time.sleep(2.0)

    # Page 2에서 "3" 찾기
    log("\n=== Finding '3' on Page 2 ===")
    result3 = driver.execute_script(FIND_SCRIPT, "3")
    data3 = json.loads(result3)
    log(f"Total DOM elements: {data3['total']}")
    log(f"Elements with text '3': {len(data3['results'])}")
    for i, item in enumerate(data3['results']):
        log(f"  [{i}] tag={item['tag']} isSwiper={item['isSwiper']}")
        log(f"       cls={item['cls']}")
        log(f"       path={item['path'][:250]}")

    log("\n=== DIAGNOSIS v2 COMPLETE ===")

finally:
    driver.quit()
    log("Driver closed.")
