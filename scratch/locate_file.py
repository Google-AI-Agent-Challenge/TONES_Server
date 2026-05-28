import os

def main():
    root = "d:\\대외 활동 자료\\Contest\\Google AI Agent Challenge\\Project"
    print(f"[*] Searching for mobile_page.html under: {root}")
    found = False
    for r, dirs, files in os.walk(root):
        if "mobile_page.html" in files:
            print(f"[+] Found at: {os.path.join(r, 'mobile_page.html')}")
            found = True
            
        if "output_elements.txt" in files:
            print(f"[+] Found output_elements.txt at: {os.path.join(r, 'output_elements.txt')}")
            found = True
            
    if not found:
        print("[!] No files found.")

if __name__ == "__main__":
    main()
