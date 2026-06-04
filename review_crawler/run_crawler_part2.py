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

# Override PRODUCT_PAGES to crawl product 2, 3, 4, 5, 6, 7
crawler.PRODUCT_PAGES = {
    "A000000206889": {"name": "스킨푸드 패드 레시피 3종 페이지", "max_scroll_steps": 300, "target_reviews": 500, "delay": 1.0},
    "A000000231714": {"name": "복숭아 패드 전용 페이지",  "max_scroll_steps": 200, "target_reviews": 250,  "delay": 0.9},
    "A000000185135": {"name": "미나리 패드 전용 페이지",  "max_scroll_steps": 200, "target_reviews": 250,  "delay": 0.9},
    "A000000248098": {"name": "당근 패드 기획전 페이지",  "max_scroll_steps": 200, "target_reviews": 250,  "delay": 0.9},
    "A000000200396": {"name": "감자 패드 전용 페이지",    "max_scroll_steps": 200, "target_reviews": 250,  "delay": 0.9},
    "A000000157075": {"name": "도토리 패드 전용 페이지",  "max_scroll_steps": 200, "target_reviews": 250,  "delay": 0.9},
}

if __name__ == "__main__":
    # Set the environment variable for output path
    os.environ["REVIEW_CSV_PATH"] = "review_crawler/data/olive_young_reviews_part2.csv"
    crawler.main()
