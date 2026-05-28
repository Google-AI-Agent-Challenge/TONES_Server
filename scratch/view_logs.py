import os

def main():
    task_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\5a14d43a-380b-4a68-9170-b1cd42b501c5\.system_generated\tasks"
    logs = []
    if os.path.exists(task_dir):
        for f in sorted(os.listdir(task_dir)):
            if f.endswith(".log"):
                path = os.path.join(task_dir, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as log:
                        content = log.read()
                        logs.append(f"=== Log: {f} ===\n{content}\n")
                except Exception as e:
                    logs.append(f"=== Error reading: {f} ===\n{e}\n")
    else:
        logs.append(f"Task dir not found: {task_dir}")
        
    logs.append("\n=== Drive D:\ Contents ===\n")
    try:
        # Filter files in D:\ root to see if mobile_page.html is there
        d_files = os.listdir("d:\\")
        filtered = [f for f in d_files if not f.startswith("$") and not f.lower().endswith(".sys")]
        logs.append(str(filtered))
    except Exception as e:
        logs.append(f"Error listing D:\\: {e}")
        
    out_path = r"d:\대외 활동 자료\Contest\Google AI Agent Challenge\Project\WooYeonChoiYeonWoo_Server\scratch\task_logs_all.txt"
    with open(out_path, "w", encoding="utf-8") as out:
        out.write("\n".join(logs))
    print(f"[*] Wrote aggregated logs to {out_path}")

if __name__ == "__main__":
    main()
