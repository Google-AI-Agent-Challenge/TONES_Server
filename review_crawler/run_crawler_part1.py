# -*- coding: utf-8 -*-
import sys
import os

# Add workspace to path
sys.path.append(os.path.abspath("."))

import app.crawler.olive_young_crawler as crawler

# Speed up sleep dynamically
import time
orig_sleep = time.sleep
def custom_sleep(seconds):
    if seconds == 2.0:
        orig_sleep(0.4)
    elif seconds == 1.5:
        orig_sleep(0.3)
    elif seconds in (1.0, 0.9):
        orig_sleep(0.2)
    else:
        orig_sleep(seconds)
crawler.time.sleep = custom_sleep

# Speed up wait_for_review_list_update
orig_wait = crawler.wait_for_review_list_update
def custom_wait(driver, prev_first_review_key, timeout=1.5):
    return orig_wait(driver, prev_first_review_key, timeout=timeout)
crawler.wait_for_review_list_update = custom_wait

# Override PRODUCT_PAGES to crawl ONLY product 1
crawler.PRODUCT_PAGES = {
    "A000000166709": {"name": "11종 통합 기획전 페이지", "max_scroll_steps": 600, "target_reviews": 1500, "delay": 1.0},
}

if __name__ == "__main__":
    # Set the environment variable for output path
    os.environ["REVIEW_CSV_PATH"] = "review_crawler/data/olive_young_reviews_part1.csv"
    crawler.main()
