import os
from bs4 import BeautifulSoup

def main():
    project_root = r"d:\대외 활동 자료\Contest\Google AI Agent Challenge\Project\WooYeonChoiYeonWoo_Server"
    html_path = os.path.join(project_root, "mobile_page.html")
    
    # Fallback to drive root if needed
    if not os.path.exists(html_path):
        drive_html = r"d:\mobile_page.html"
        if os.path.exists(drive_html):
            html_path = drive_html
            print(f"[+] Found mobile_page.html in drive root: {drive_html}")
            
    if not os.path.exists(html_path):
        print(f"[!] mobile_page.html not found anywhere!")
        return
        
    print(f"[*] Reading HTML from: {html_path}")
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
        
    out_path = os.path.join(project_root, "scratch", "output_elements.txt")
    print(f"[*] Writing elements to absolute path: {out_path}")
    with open(out_path, "w", encoding="utf-8") as out:
        out.write("Review Elements found in HTML:\n")
        for el in soup.find_all(class_=True):
            classes = el.get("class")
            cls_str = " ".join(classes).lower()
            if any(k in cls_str for k in ["gdas", "review", "point", "date", "user", "option"]):
                out.write(f"Tag: {el.name}, Class: {classes}, Text: {el.text.strip()[:150]}\n")
                
    print("[*] Completed successfully!")

if __name__ == "__main__":
    main()
