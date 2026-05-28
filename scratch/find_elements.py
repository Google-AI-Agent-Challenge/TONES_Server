from bs4 import BeautifulSoup

def main():
    with open("mobile_page.html", "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    with open("scratch/output_elements.txt", "w", encoding="utf-8") as out:
        out.write("Review Elements found in HTML:\n")
        # Let's inspect elements with review, gdas, user, date, option in classes
        for el in soup.find_all(class_=True):
            classes = el.get("class")
            cls_str = " ".join(classes).lower()
            if any(k in cls_str for k in ["gdas", "review", "point", "date", "user", "option"]):
                out.write(f"Tag: {el.name}, Class: {classes}, Text: {el.text.strip()[:150]}\n")

if __name__ == "__main__":
    main()
