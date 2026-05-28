import os

def main():
    root = "d:\\대외 활동 자료\\Contest\\Google AI Agent Challenge\\Project"
    results = []
    
    # Search for mobile_page.html
    html_path = None
    for r, dirs, files in os.walk(root):
        if "node_modules" in r or ".next" in r or ".git" in r:
            continue
        if "mobile_page.html" in files:
            html_path = os.path.join(r, 'mobile_page.html')
            break
            
    if html_path and os.path.exists(html_path):
        size = os.path.getsize(html_path)
        results.append(f"Found mobile_page.html at: {html_path}")
        results.append(f"Size: {size} bytes")
        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(1000)
            results.append(f"First 1000 chars:\n{content}")
    else:
        results.append("mobile_page.html NOT found.")
        
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(script_dir, "mobile_size.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(results))
    print(f"[*] Wrote output to {out_path}")

if __name__ == "__main__":
    main()
