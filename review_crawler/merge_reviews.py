# -*- coding: utf-8 -*-
import pandas as pd
import os

def merge_csv_files():
    file1 = "review_crawler/data/olive_young_reviews_part1.csv"
    file2 = "review_crawler/data/olive_young_reviews_part2.csv"
    output_file = "review_crawler/data/olive_young_reviews.csv"
    
    dfs = []
    
    if os.path.exists(file1):
        df1 = pd.read_csv(file1)
        if not df1.empty:
            print(f"[MERGE] Loaded {file1} with {len(df1)} rows.")
            dfs.append(df1)
            
    if os.path.exists(file2):
        df2 = pd.read_csv(file2)
        if not df2.empty:
            print(f"[MERGE] Loaded {file2} with {len(df2)} rows.")
            dfs.append(df2)
            
    if not dfs:
        print("[MERGE] No CSV files found to merge.")
        return
        
    merged_df = pd.concat(dfs, ignore_index=True)
    before_dedupe = len(merged_df)
    
    # Deduplicate by review_key
    if "review_key" in merged_df.columns:
        merged_df = merged_df.drop_duplicates(subset=["review_key"], keep="first")
        
    after_dedupe = len(merged_df)
    print(f"[MERGE] Merged and deduplicated: before={before_dedupe} after={after_dedupe} reviews.")
    
    # Save the merged result
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    merged_df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"[MERGE] Merged CSV saved to {output_file} with {len(merged_df)} rows.")

if __name__ == "__main__":
    merge_csv_files()
