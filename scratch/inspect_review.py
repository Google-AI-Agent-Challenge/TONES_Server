import time
import json
import os
import sys
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By

EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def init_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=375,812")
    options.binary_location = EDGE_BINARY_PATH
    options.add_argument(
        "user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
    )
    driver = webdriver.Edge(options=options)
    return driver

_INTERCEPTOR_JS = """
if (!window.__oyIntercepted) {
    window.__oyIntercepted = true;
    window.__oyBatches    = [];

    const _xOpen = XMLHttpRequest.prototype.open;
    const _xSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(m, u) {
        this._oy_url = String(u || '');
        return _xOpen.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function() {
        this.addEventListener('load', function() {
            if ((this._oy_url || '').includes('/review/api/')) {
                window.__oyBatches.push({
                    src: 'xhr', url: this._oy_url,
                    status: this.status, body: this.responseText || ''
                });
            }
        });
        return _xSend.apply(this, arguments);
    };

    const _origFetch = window.fetch;
    window.fetch = async function(input, init) {
        const url = typeof input === 'string' ? input : ((input && input.url) || '');
        const res = await _origFetch.apply(this, arguments);
        if (url.includes('/review/api/')) {
            try {
                const text = await res.clone().text();
                window.__oyBatches.push({
                    src: 'fetch', url: url,
                    status: res.status, body: text || ''
                });
            } catch(e) {}
        }
        return res;
    };
}
"""

_COLLECT_BATCHES_JS = """
const b = (window.__oyBatches || []).slice();
window.__oyBatches = [];
return JSON.stringify(b);
"""

def main():
    driver = init_driver()
    try:
        url = "https://m.oliveyoung.co.kr/m/goods/getGoodsDetail.do?goodsNo=A000000157075"
        print(f"Loading {url}...")
        driver.get(url)
        time.sleep(5.0)
        
        driver.execute_script(_INTERCEPTOR_JS)
        print("Interceptor injected.")
        
        # Find review tab
        clicked = False
        for el in driver.find_elements(By.CSS_SELECTOR, "[class*='GoodsDetailTabs'] li, button, a"):
            txt = el.text.strip()
            if '리뷰' in txt:
                driver.execute_script("arguments[0].click();", el)
                print(f"Clicked review tab: {txt}")
                clicked = True
                break
        
        if not clicked:
            print("Failed to click review tab via CSS, trying XPath...")
            for el in driver.find_elements(By.XPATH, "//*[contains(text(), '리뷰')]"):
                driver.execute_script("arguments[0].click();", el)
                print(f"Clicked review tab (XPath): {el.text}")
                break
                
        time.sleep(5.0)
        
        # Collect batches
        raw = driver.execute_script(_COLLECT_BATCHES_JS)
        batches = json.loads(raw or '[]')
        print(f"Collected {len(batches)} batches.")
        
        os.makedirs("scratch", exist_ok=True)
        with open("scratch/api_batches.json", "w", encoding="utf-8") as f:
            json.dump(batches, f, ensure_ascii=False, indent=2)
            
        print("Saved to scratch/api_batches.json")
        
        # Also print the DOM structure of a review item to check for skin types
        dom_dump = driver.execute_script("""
            function findDeep(root, tag) {
                if (!root) return null;
                const el = root.querySelector ? root.querySelector(tag) : null;
                if (el) return el;
                for (const e of (root.querySelectorAll ? Array.from(root.querySelectorAll('*')) : [])) {
                    if (e.shadowRoot) { const r = findDeep(e.shadowRoot, tag); if (r) return r; }
                }
                return null;
            }
            const comp = document.querySelector('oy-review-review-in-product');
            if (!comp || !comp.shadowRoot) return "comp or shadowRoot not found";
            const list = findDeep(comp.shadowRoot, 'oy-review-review-list');
            if (!list || !list.shadowRoot) return "list or shadowRoot not found";
            const item = list.shadowRoot.querySelector('oy-review-review-item');
            if (!item || !item.shadowRoot) return "item or shadowRoot not found";
            
            // return some outer HTML of key subcomponents
            const sr = item.shadowRoot;
            const res = {
                item_html: sr.innerHTML,
                user_html: sr.querySelector('oy-review-review-user') ? sr.querySelector('oy-review-review-user').shadowRoot.innerHTML : 'no-user',
                content_html: sr.querySelector('oy-review-review-content') ? sr.querySelector('oy-review-review-content').shadowRoot.innerHTML : 'no-content'
            };
            return res;
        """)
        with open("scratch/dom_dump.json", "w", encoding="utf-8") as f:
            json.dump(dom_dump, f, ensure_ascii=False, indent=2)
        print("Saved to scratch/dom_dump.json")
        
    finally:
        driver.quit()

if __name__ == '__main__':
    main()
