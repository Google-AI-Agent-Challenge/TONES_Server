import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options
import sys
import os

EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def main():
    options = Options()
    options.add_argument("--window-size=375,812")
    options.binary_location = EDGE_BINARY_PATH
    options.add_argument(
        "user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
    )
    # Enable browser logs collection
    options.set_capability("ms:loggingPrefs", {"browser": "ALL"})
    
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Edge(options=options)
    try:
        url = "https://m.oliveyoung.co.kr/m/goods/getGoodsDetail.do?goodsNo=A000000166709"
        driver.get(url)
        time.sleep(6)
        
        # 리뷰 탭 클릭 시도
        driver.execute_script("""
            document.querySelectorAll('button,li,span,a').forEach(el => {
                if (el.textContent.includes('리뷰') && el.offsetWidth > 0) {
                    try { el.click(); } catch(e) {}
                }
            });
        """)
        time.sleep(4)
        
        # Shadow DOM 트리 덤프 스크립트 (콘솔 로그로 출력)
        dump_js = """
        function dumpTree(root, indent = 0) {
            if (!root) return '';
            let result = '';
            const children = Array.from(root.children || []);
            for (const el of children) {
                const tag = el.tagName.toLowerCase();
                const text = el.textContent.trim().replace(/\\s+/g, ' ').substring(0, 40);
                const w = el.offsetWidth;
                const h = el.offsetHeight;
                const id = el.id || '';
                const cls = el.className || '';
                
                result += ' '.repeat(indent) + `<${tag} id="${id}" class="${cls}" w="${w}" h="${h}">: "${text}"\\n`;
                if (el.shadowRoot) {
                    result += ' '.repeat(indent + 2) + `[SHADOW_ROOT]\\n`;
                    result += dumpTree(el.shadowRoot, indent + 4);
                }
                
                if (el.children && el.children.length > 0) {
                    result += dumpTree(el, indent + 2);
                }
            }
            return result;
        }
        console.log("=== SHADOW DOM DUMP START ===");
        console.log(dumpTree(document.body));
        console.log("=== SHADOW DOM DUMP END ===");
        """
        
        driver.execute_script(dump_js)
        time.sleep(2.0)
        
        # 브라우저 콘솔 로그 가져오기
        logs = driver.get_log('browser')
        dump_lines = []
        is_dumping = False
        
        for entry in logs:
            msg = entry.get('message', '')
            # Chrome/Edge console log message format: "url line:col \"message\""
            # Extract only the actual message content
            if "=== SHADOW DOM DUMP START ===" in msg:
                is_dumping = True
                continue
            if "=== SHADOW DOM DUMP END ===" in msg:
                is_dumping = False
                break
            if is_dumping:
                # Remove quotes if present
                cleaned_msg = msg
                if '\\n' in msg:
                    parts = msg.split(' ')
                    # usually console logs are like console-api 21:20 "message\nline..."
                    # Find first quote
                    q_start = msg.find('"')
                    q_end = msg.rfind('"')
                    if q_start != -1 and q_end != -1:
                        cleaned_msg = msg[q_start+1:q_end]
                # Replace escaped newlines
                cleaned_msg = cleaned_msg.replace('\\n', '\n').replace('\\t', '\t')
                dump_lines.append(cleaned_msg)
                
        with open("shadow_dump.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(dump_lines))
        print("[*] shadow_dump.txt 생성 성공!")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
