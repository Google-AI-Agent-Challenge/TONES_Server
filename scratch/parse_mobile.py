import os
from bs4 import BeautifulSoup

def main():
    path = "mobile_page.html"
    if not os.path.exists(path):
        print(f"[!] {path} not found in current directory: {os.getcwd()}")
        # Check in scratch or project root
        return
        
    print(f"[*] Reading {path}...")
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
        
    soup = BeautifulSoup(html, "html.parser")
    print(f"[*] HTML length: {len(html)} characters")
    
    # Let's search for some review keywords
    print("\n[*] Searching for review text elements:")
    # We look for common tags or tags containing review in class
    all_tags = soup.find_all()
    print(f"Total HTML elements: {len(all_tags)}")
    
    # Find list items or elements containing class with 'review' or 'gdas'
    review_containers = soup.find_all(class_=lambda x: x and ('gdas' in str(x).lower() or 'review' in str(x).lower()))
    print(f"Found {len(review_containers)} review-related elements.")
    for idx, el in enumerate(review_containers[:15]):
        print(f"[{idx}] Tag: {el.name}, Class: {el.get('class')}, Text (len={len(el.text.strip())}): {el.text.strip()[:60]}...")

if __name__ == "__main__":
    main()
