import sys
import os
import traceback

def main():
    project_root = r"d:\대외 활동 자료\Contest\Google AI Agent Challenge\Project\WooYeonChoiYeonWoo_Server"
    sys.path.insert(0, project_root)
    
    out_path = os.path.join(project_root, "test_crawl_output.txt")
    with open(out_path, "w", encoding="utf-8") as out:
        out.write("Starting test_crawl.main()...\n")
        try:
            from scratch.test_crawl import main as crawl_main
            crawl_main()
            out.write("Successfully completed test_crawl.main()!\n")
        except Exception as e:
            out.write(f"Exception raised:\n{e}\n")
            out.write("Traceback:\n")
            traceback.print_exc(file=out)
            
    print(f"[*] Done. Results written to {out_path}")

if __name__ == "__main__":
    main()
