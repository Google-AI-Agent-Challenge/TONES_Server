# -*- coding: utf-8 -*-
"""
Dumps the FULL pagination shadow DOM after clicking Page 2,
so we can see the exact HTML structure and button selectors.
Run: python scratch/dump_pagination.py
"""

import os
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By

EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
goods_no = "A000000166709"
url = f"https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo={goods_no}"

print("=== Olive Young Pagination DOM Inspector ===")
print(f"Target: {url}")

options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.binary_location = EDGE_BINARY_PATH
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Edge(options=options)
try:
    print(f"\n[1] Opening page...")
    driver.get(url)
    time.sleep(6)

    print("[2] Scrolling and clicking reviews tab...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3);")
    time.sleep(1.5)

    buttons = driver.find_elements(By.TAG_NAME, "button")
    for btn in buttons:
        txt = btn.text
        if "리뷰&셔터" in txt or "리뷰 " in txt:
            driver.execute_script("arguments[0].click();", btn)
            print(f"   Reviews tab clicked! ({txt})")
            break

    time.sleep(4)

    # Scroll into the review area
    driver.execute_script("""
        let el = document.querySelector('oy-review-review-in-product');
        if (el) el.scrollIntoView({behavior: 'instant', block: 'center'});
        else window.scrollTo(0, document.body.scrollHeight * 0.45);
    """)
    time.sleep(2)
    driver.execute_script("window.scrollBy(0, 500);")
    time.sleep(2)

    # --- Step A: Dump Page 1 pagination HTML ---
    print("\n[3] Dumping Page 1 pagination shadow DOM...")
    dump_script = """
    function dumpShadowDOM(root, indent) {
        if (!root) return '(null)';
        let html = root.innerHTML || '';
        // Also collect all shadow roots recursively
        let all = Array.from(root.querySelectorAll('*'));
        let result = 'OUTER HTML:\\n' + html.substring(0, 3000);
        for (let el of all) {
            if (el.shadowRoot) {
                result += '\\n\\n=== SHADOW ROOT of <' + el.tagName + '.' + (el.className||'') + '> ===\\n';
                result += el.shadowRoot.innerHTML.substring(0, 3000);
            }
        }
        return result;
    }

    let inProd = document.querySelector('oy-review-review-in-product');
    if (!inProd) return 'NOT FOUND: oy-review-review-in-product';
    let root1 = inProd.shadowRoot;
    if (!root1) return 'NOT FOUND: shadowRoot of oy-review-review-in-product';

    return dumpShadowDOM(root1, '');
    """
    result = driver.execute_script(dump_script)
    with open("scratch/page1_pagination.html", "w", encoding="utf-8") as f:
        f.write(result or "(empty)")
    print(f"   Saved to scratch/page1_pagination.html ({len(result or '')} chars)")

    # --- Step B: Click Page 2 using the known working approach ---
    print("\n[4] Clicking Page 2 button...")
    click_p2 = """
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
    collect(document.documentElement);

    let found = false;
    for (let el of allEls) {
        let t = el.textContent.trim();
        if (t === '2') {
            let path = '';
            let cur = el;
            let d = 0;
            while (cur && d < 10) {
                path += (cur.tagName||'') + '.' + (cur.className||'') + ' > ';
                cur = cur.parentNode || cur.host;
                d++;
            }
            console.log('[P2 click] candidate: text=' + t + ' path=' + path.substring(0,120));
            el.click();
            found = true;
            break;
        }
    }
    return found;
    """
    clicked = driver.execute_script(click_p2)
    print(f"   Page 2 click result: {clicked}")
    time.sleep(3)
    driver.execute_script("window.scrollBy(0, 300);")
    time.sleep(2)

    # --- Step C: Dump Page 2 pagination HTML ---
    print("\n[5] Dumping Page 2 pagination shadow DOM (looking for '3' button)...")
    result2 = driver.execute_script(dump_script)
    with open("scratch/page2_pagination.html", "w", encoding="utf-8") as f:
        f.write(result2 or "(empty)")
    print(f"   Saved to scratch/page2_pagination.html ({len(result2 or '')} chars)")

    # --- Step D: Find all elements with text "3" ---
    print("\n[6] Finding ALL elements with text '3' after Page 2 click...")
    find_3 = """
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
    collect(document.documentElement);

    let results = [];
    for (let el of allEls) {
        let text = el.textContent.trim();
        let directText = Array.from(el.childNodes)
            .filter(n => n.nodeType === Node.TEXT_NODE)
            .map(n => n.textContent.trim())
            .join('');
        if (directText === '3' || text === '3') {
            let path = '';
            let cur = el;
            let d = 0;
            while (cur && d < 12) {
                path += (cur.tagName||'') + '.' + (cur.className||'') + ' > ';
                cur = cur.parentNode || cur.host;
                d++;
            }
            results.push({
                tag: el.tagName,
                cls: el.className,
                id: el.id,
                directText: directText,
                fullText: text.substring(0, 30),
                path: path.substring(0, 200)
            });
        }
    }
    return JSON.stringify(results, null, 2);
    """
    find_result = driver.execute_script(find_3)
    with open("scratch/find_page3_button.json", "w", encoding="utf-8") as f:
        f.write(find_result or "[]")
    print(f"   Saved to scratch/find_page3_button.json")
    print(f"   Content preview:\n{(find_result or '[]')[:2000]}")

finally:
    driver.quit()
    print("\n=== Done ===")
