# -*- coding: utf-8 -*-
import os
import sys
import json
import csv
import time
import requests

# Reconfigure stdout to support UTF-8 printing
sys.stdout.reconfigure(encoding='utf-8')

PRODUCTS = {
    "A000000166709": "11종 통합 기획전 페이지",
    "A000000206889": "스킨푸드 패드 레시피 3종 페이지",
    "A000000231714": "복숭아 패드 전용 페이지",
    "A000000185135": "미나리 패드 전용 페이지",
    "A000000248098": "당근 패드 기획전 페이지",
    "A000000200396": "감자 패드 전용 페이지"
}

# Mapping of goods_no to default option name if empty
DEFAULT_OPTIONS = {
    "A000000166709": "[흔적진정]감자패드60매(+10매기획)",
    "A000000206889": " [당근/수분진정] 60매+30매 기획",
    "A000000231714": "[화잘먹]복숭아패드70매",
    "A000000185135": "[긴급진정]미나리패드60매+(10매기획)",
    "A000000248098": "[수분진정]당근패드60매(+10매기획)",
    "A000000200396": "[흔적진정]감자패드60매(+10매기획)"
}

URL = "https://m.oliveyoung.co.kr/review/api/v2/reviews/cursor"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Content-Type": "application/json",
    "Origin": "https://m.oliveyoung.co.kr"
}

def fetch_reviews_for_product(goods_no, sort_type, target_count=350):
    reviews_collected = []
    
    payload = {
        "goodsNumber": goods_no,
        "page": 0,
        "size": 50,
        "sortType": sort_type,
        "reviewType": "ALL"
    }
    
    cursor_id = None
    cursor_score = None
    cursor_count = None
    has_next = True
    
    print(f"Starting fetch for {goods_no} with sort {sort_type}...")
    
    while len(reviews_collected) < target_count and has_next:
        req_payload = payload.copy()
        if cursor_id is not None:
            req_payload["cursorId"] = cursor_id
            req_payload["cursorScore"] = cursor_score
            if cursor_count is not None:
                req_payload["cursorCount"] = cursor_count
                
        try:
            r = requests.post(URL, headers=HEADERS, json=req_payload, timeout=10)
            if r.status_code != 200:
                print(f"Error status {r.status_code}")
                break
                
            res = r.json()
            data = res.get('data', {})
            batch = data.get('goodsReviewList', [])
            if not batch:
                break
                
            reviews_collected.extend(batch)
            
            cursor_id = data.get('nextCursorId')
            cursor_score = data.get('nextCursorScore')
            cursor_count = data.get('nextCursorCount')
            has_next = data.get('hasNext', False)
            
            print(f"Fetched {len(reviews_collected)} reviews so far...")
            
            # Gentle throttling
            time.sleep(0.3)
        except Exception as e:
            print(f"Request failed: {e}")
            break
            
    return reviews_collected

def main():
    all_reviews = {}  # review_key -> review_row dict to deduplicate
    unique_option_names = set()
    
    for goods_no, name in PRODUCTS.items():
        print(f"\n=== Processing product: {goods_no} ({name}) ===")
        # Get latest reviews
        latest = fetch_reviews_for_product(goods_no, "DATETIME_DESC", 300)
        # Get helpful reviews
        helpful = fetch_reviews_for_product(goods_no, "USEFUL_SCORE_DESC", 200)
        
        for r in latest + helpful:
            review_key = str(r.get('reviewId'))
            if not review_key or review_key == 'None':
                continue
                
            goods_dto = r.get('goodsDto', {})
            profile_dto = r.get('profileDto', {}) or {}
            
            option_name = goods_dto.get('optionName', '').strip()
            if not option_name:
                option_name = DEFAULT_OPTIONS.get(goods_no, '')
                
            unique_option_names.add(option_name)
                
            # Parse skin types
            skin_types_list = []
            if profile_dto.get('skinType'):
                skin_types_list.append(profile_dto['skinType'])
            if profile_dto.get('skinTone'):
                skin_types_list.append(profile_dto['skinTone'])
            if profile_dto.get('skinTrouble'):
                skin_types_list.extend(profile_dto['skinTrouble'])
            skin_types_str = ", ".join(skin_types_list)
            
            rating = r.get('reviewScore', 5)
            date_str = r.get('createdDateTime', '')
            content = r.get('content', '')
            username = profile_dto.get('memberNickname', '')
            
            row = {
                "goods_no": goods_no,
                "option_name": option_name,
                "username": username,
                "skin_types": skin_types_str,
                "rating": rating,
                "date": date_str,
                "content": content,
                "filter_type": "api_crawled",
                "review_key": review_key,
                "skin_type": "",
                "sort_type": ""
            }
            all_reviews[review_key] = row
            
    print(f"\nTotal unique reviews collected: {len(all_reviews)}")
    print(f"Unique option names found ({len(unique_option_names)}):")
    for opt in sorted(unique_option_names):
        print(f"  - {opt}")
        
    # Write to olive_young_reviews.csv
    out_dir = "review_crawler/data"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "olive_young_reviews.csv")
    
    fieldnames = [
        "goods_no", "option_name", "username", "skin_types", "rating",
        "date", "content", "filter_type", "review_key", "skin_type", "sort_type"
    ]
    
    with open(out_path, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r_key in sorted(all_reviews.keys()):
            writer.writerow(all_reviews[r_key])
            
    print(f"\nSuccessfully wrote {len(all_reviews)} reviews to {out_path}")

if __name__ == "__main__":
    main()
