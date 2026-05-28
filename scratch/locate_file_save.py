import os

def main():
    root = "d:\\대외 활동 자료\\Contest\\Google AI Agent Challenge\\Project"
    results = []
    results.append(f"[*] Searching for mobile_page.html under: {root}")
    
    for r, dirs, files in os.walk(root):
        if "node_modules" in r or ".next" in r or ".git" in r:
            continue
        if "mobile_page.html" in files:
            results.append(f"[+] Found mobile_page.html at: {os.path.join(r, 'mobile_page.html')}")
        if "output_elements.txt" in files:
            results.append(f"[+] Found output_elements.txt at: {os.path.join(r, 'output_elements.txt')}")
            
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(script_dir, "location_results.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(results))
    print(f"[*] Wrote search results to {out_path}")

if __name__ == "__main__":
    main()
