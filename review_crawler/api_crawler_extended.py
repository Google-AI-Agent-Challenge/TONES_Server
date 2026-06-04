# -*- coding: utf-8 -*-
"""
확장 API 크롤러: DB/CSV에 이미 존재하는 리뷰를 제외하고
최신순·별점높은순·별점낮은순 3가지 정렬로 신규 리뷰만 수집
"""
import os
import sys
import json
import csv
import time
import requests
import pandas as pd

sys.path.append(os.path.abspath("."))
sys.stdout.reconfigure(encoding='utf-8')

# ──────────────────────────────────────────────────────────
# 상품 목록 (개별 상품 페이지)
# ──────────────────────────────────────────────────────────
PRODUCTS = {
    "A000000166709": "11종 통합 기획전 페이지",
    "A000000206889": "스킨푸드 패드 레시피 3종 페이지",
    "A000000231714": "복숭아 패드 전용 페이지",
    "A000000185135": "미나리 패드 전용 페이지",
    "A000000248098": "당근 패드 기획전 페이지",
    "A000000200396": "감자 패드 전용 페이지",
    "A000000157075": "도토리 패드 전용 페이지",
}

# 정렬 유형
SORT_TYPES = [
    "DATETIME_DESC",     # 최신순
    "SCORE_DESC",        # 별점 높은순
    "SCORE_ASC",         # 별점 낮은순
    "USEFUL_SCORE_DESC", # 도움순
]

DEFAULT_OPTIONS = {
    "A000000166709": "[흔적진정]감자패드60매(+10매기획)",
    "A000000206889": " [당근/수분진정] 60매+30매 기획",
    "A000000231714": "[화잘먹]복숭아패드70매",
    "A000000185135": "[긴급진정]미나리패드60매+(10매기획)",
    "A000000248098": "[수분진정]당근패드60매(+10매기획)",
    "A000000200396": "[흔적진정]감자패드60매(+10매기획)",
    "A000000157075": "[흔적진정]도토리패드60매(+10매기획)",
}

URL = "https://m.oliveyoung.co.kr/review/api/v2/reviews/cursor"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
                  "Mobile/15E148 Safari/604.1",
    "Content-Type": "application/json",
    "Origin": "https://m.oliveyoung.co.kr",
}


def load_existing_keys():
    """DB + 기존 CSV에서 이미 수집된 review_key 집합 반환"""
    keys = set()

    # 1. DB 로드
    try:
        from app.database.connection import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT review_id FROM reviews WHERE review_id IS NOT NULL;")
        db_keys = [str(r[0]) for r in cursor.fetchall() if r[0]]
        keys.update(db_keys)
        print(f"[DB] 기존 리뷰 키 {len(db_keys)}개 로드")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[DB_ERROR] {e}")

    # 2. CSV 로드
    csv_files = [
        "review_crawler/data/olive_young_reviews.csv",
        "review_crawler/data/olive_young_reviews_part1.csv",
        "review_crawler/data/olive_young_reviews_part2.csv",
    ]
    for csv_path in csv_files:
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                if "review_key" in df.columns:
                    csv_keys = df["review_key"].dropna().astype(str).tolist()
                    keys.update(csv_keys)
                    print(f"[CSV] {csv_path} → {len(csv_keys)}개 키 로드")
            except Exception as e:
                print(f"[CSV_ERROR] {csv_path}: {e}")

    print(f"[TOTAL] 기존 수집 리뷰 키 합계: {len(keys)}개")
    return keys


def fetch_reviews(goods_no, sort_type, existing_keys, target_new=300):
    """지정 상품 + 정렬로 리뷰 수집 (기존 키 제외)"""
    new_reviews = []
    seen_keys = set()
    consecutive_dup = 0

    payload = {
        "goodsNumber": goods_no,
        "page": 0,
        "size": 50,
        "sortType": sort_type,
        "reviewType": "ALL",
    }

    cursor_id = None
    cursor_score = None
    cursor_count = None
    has_next = True
    page = 0

    while len(new_reviews) < target_new and has_next and page < 40:
        req = payload.copy()
        if cursor_id is not None:
            req["cursorId"] = cursor_id
            req["cursorScore"] = cursor_score
            if cursor_count is not None:
                req["cursorCount"] = cursor_count

        try:
            r = requests.post(URL, headers=HEADERS, json=req, timeout=15)
            if r.status_code != 200:
                print(f"  [ERROR] status={r.status_code}")
                break

            res = r.json()
            data = res.get("data", {})
            batch = data.get("goodsReviewList", [])
            if not batch:
                break

            batch_new = 0
            for item in batch:
                rk = str(item.get("reviewId", ""))
                if not rk or rk == "None":
                    continue
                if rk in existing_keys or rk in seen_keys:
                    continue
                seen_keys.add(rk)
                new_reviews.append(item)
                batch_new += 1

            if batch_new == 0:
                consecutive_dup += 1
                if consecutive_dup >= 3:
                    print(f"  연속 3회 중복만 → 정렬 종료")
                    break
            else:
                consecutive_dup = 0

            cursor_id = data.get("nextCursorId")
            cursor_score = data.get("nextCursorScore")
            cursor_count = data.get("nextCursorCount")
            has_next = data.get("hasNext", False)
            page += 1

            print(f"  page={page} batch={len(batch)} new={batch_new} total_new={len(new_reviews)}")
            time.sleep(0.35)

        except Exception as e:
            print(f"  [REQUEST_ERROR] {e}")
            break

    return new_reviews


def parse_review(item, goods_no):
    """API 응답 아이템 → CSV row dict"""
    goods_dto = item.get("goodsDto", {})
    profile_dto = item.get("profileDto", {}) or {}

    option_name = goods_dto.get("optionName", "").strip()
    if not option_name:
        option_name = DEFAULT_OPTIONS.get(goods_no, "단품")

    skin_types_list = []
    if profile_dto.get("skinType"):
        skin_types_list.append(profile_dto["skinType"])
    if profile_dto.get("skinTone"):
        skin_types_list.append(profile_dto["skinTone"])
    if profile_dto.get("skinTrouble"):
        skin_types_list.extend(profile_dto["skinTrouble"])

    return {
        "goods_no": goods_no,
        "option_name": option_name,
        "username": profile_dto.get("memberNickname", ""),
        "skin_types": ", ".join(skin_types_list),
        "rating": item.get("reviewScore", 5),
        "date": item.get("createdDateTime", ""),
        "content": item.get("content", ""),
        "filter_type": "api_crawled",
        "review_key": str(item.get("reviewId", "")),
        "skin_type": "",
        "sort_type": "",
    }


def main():
    existing_keys = load_existing_keys()
    all_new = {}  # review_key → row

    for goods_no, name in PRODUCTS.items():
        print(f"\n{'='*60}")
        print(f"  {goods_no} — {name}")
        print(f"{'='*60}")

        for sort_type in SORT_TYPES:
            print(f"\n  [SORT] {sort_type}")
            items = fetch_reviews(goods_no, sort_type, existing_keys, target_new=250)

            for item in items:
                rk = str(item.get("reviewId", ""))
                if rk not in all_new:
                    all_new[rk] = parse_review(item, goods_no)
                    existing_keys.add(rk)  # 이후 중복 방지

            print(f"  → 신규 {len(items)}건 수집 (누적 고유: {len(all_new)}건)")

    # CSV 저장
    out_dir = "review_crawler/data"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "olive_young_reviews_ext.csv")

    fieldnames = [
        "goods_no", "option_name", "username", "skin_types", "rating",
        "date", "content", "filter_type", "review_key", "skin_type", "sort_type",
    ]

    with open(out_path, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rk in sorted(all_new.keys()):
            writer.writerow(all_new[rk])

    print(f"\n{'='*60}")
    print(f"  총 신규 리뷰: {len(all_new)}건 → {out_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
