# -*- coding: utf-8 -*-
import argparse
import csv
import html
import json
import os
import re
import sys
import requests

def parse_date(raw: str) -> str | None:
    """날짜 구분자(. 또는 /)를 -로 변환하고 YYYY-MM-DD 포맷을 검증합니다."""
    cleaned = str(raw).strip()
    if not cleaned or cleaned.lower() in ("nan", "none", "null", ""):
        return None

    # 구분자 변환 (. 이나 / -> -)
    cleaned = cleaned.replace(".", "-").replace("/", "-")

    # YYYY-MM-DD 정규식 매칭
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", cleaned)
    if m:
        # 정상적인 날짜 형식인지 체크하기 위해 슬라이싱
        date_str = m.group(0)
        try:
            # 단순 파싱 확인
            parts = [int(p) for p in date_str.split("-")]
            if len(parts) == 3:
                # 간단한 일수 범위 체크
                year, month, day = parts
                if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                    return date_str
        except ValueError:
            pass

    return None

def main():
    parser = argparse.ArgumentParser(description="CSV reviews to Bulk API adapter")
    parser.add_argument("--csv-path", type=str, default="review_crawler/data/olive_young_reviews.csv")
    parser.add_argument("--map-path", type=str, default="review_crawler/product_map.json")
    parser.add_argument("--api-url", type=str, default="http://127.0.0.1:8000/api/v1/reviews/bulk")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--chunk-size", type=int, default=5)
    args = parser.parse_args()

    # 1. product_map.json 로드
    if not os.path.exists(args.map_path):
        print(f"[ERROR] Map file not found: {args.map_path}")
        sys.exit(1)
    
    with open(args.map_path, "r", encoding="utf-8") as f:
        product_map = json.load(f)

    # 2. CSV 로드
    if not os.path.exists(args.csv_path):
        print(f"[ERROR] CSV file not found: {args.csv_path}")
        sys.exit(1)

    rows = []
    with open(args.csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"[CSV] loaded_rows={len(rows)}")

    # 3. review_key 기준 중복 제거
    seen_keys = set()
    deduped_rows = []
    for row in rows:
        key = row.get("review_key")
        if key:
            key = str(key).strip()
        if not key:
            # review_key가 누락된 행은 우선 중복 제거에선 지나가고 validate에서 스킵 로깅 처리
            deduped_rows.append(row)
            continue
        if key not in seen_keys:
            seen_keys.add(key)
            deduped_rows.append(row)

    # 중복 제거 통계 로깅
    print(f"[DEDUPE] before={len(rows)} after={len(deduped_rows)}")

    # 4. 행별 검증 및 매핑
    valid_payloads = []
    skipped = 0
    map_success = 0
    map_failed = 0

    for row in deduped_rows:
        option_name = row.get("option_name")
        content = row.get("content")
        rating_raw = row.get("rating")
        date_raw = row.get("date")
        review_key = row.get("review_key")

        # 1) review_key 누락 검사
        if not review_key or not str(review_key).strip():
            print("[SKIP] reason=review_key_missing")
            skipped += 1
            continue
        review_key_str = str(review_key).strip()

        # 2) option_name 누락 검사
        if not option_name or not str(option_name).strip():
            print(f"[SKIP] reason=option_name_missing review_key={review_key_str}")
            skipped += 1
            continue
        option_name_str = str(option_name).strip()

        # 3) content 누락 검사
        if not content or not str(content).strip():
            print(f"[SKIP] reason=content_missing review_key={review_key_str}")
            skipped += 1
            continue
        content_str = str(content).strip()

        # 4) rating 검사 (1~5 정수만 허용)
        try:
            rating = float(rating_raw)
            if not rating.is_integer() or not (1 <= rating <= 5):
                raise ValueError
            rating_val = int(rating)
        except (ValueError, TypeError):
            print(f"[SKIP] reason=invalid_rating review_key={review_key_str}")
            skipped += 1
            continue

        # 5) 날짜 검사
        parsed_date = parse_date(date_raw)
        if not parsed_date:
            print(f"[SKIP] reason=date_parse_failed review_key={review_key_str}")
            skipped += 1
            continue

        # 6) 상품 매핑 검사
        product_id = product_map.get(option_name_str)
        if not product_id:
            print(f"[SKIP] reason=product_mapping_missing option_name={option_name_str}")
            map_failed += 1
            skipped += 1
            continue

        map_success += 1
        
        # HTML 엔티티 복원
        unescaped_content = html.unescape(content_str)

        payload = {
            "product_id": product_id,
            "content": unescaped_content,
            "rating": rating_val,
            "reviewer_type": "general",
            "source": "olive_young",
            "review_date": parsed_date,
            "review_id": review_key_str
        }
        valid_payloads.append(payload)

    print(f"[VALIDATE] valid={len(valid_payloads)} skipped={skipped}")
    print(f"[MAP] success={map_success} failed={map_failed}")

    # 5. limit 적용
    if args.limit is not None and args.limit > 0:
        valid_payloads = valid_payloads[:args.limit]

    # 6. 업로드 또는 dry-run
    if args.dry_run:
        print("[DRY_RUN] no_request_sent")
        return

    # Bulk 업로드 진행
    total_success = 0
    total_failed = 0
    total_payloads = len(valid_payloads)

    for i in range(0, total_payloads, args.chunk_size):
        chunk = valid_payloads[i:i+args.chunk_size]
        try:
            res = requests.post(args.api_url, json=chunk, headers={"Content-Type": "application/json"}, timeout=180)
            if res.status_code in (200, 201):
                total_success += len(chunk)
                print(f"[UPLOAD] chunk={i//args.chunk_size + 1} sent={len(chunk)} success={len(chunk)} failed=0")
            else:
                total_failed += len(chunk)
                print(f"[UPLOAD] chunk={i//args.chunk_size + 1} sent={len(chunk)} success=0 failed={len(chunk)}")
        except Exception as e:
            total_failed += len(chunk)
            print(f"[UPLOAD] chunk={i//args.chunk_size + 1} sent={len(chunk)} success=0 failed={len(chunk)}")

    print(f"[UPLOAD_DONE] success={total_success} failed={total_failed}")

if __name__ == "__main__":
    main()
