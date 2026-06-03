# -*- coding: utf-8 -*-
# [FIX] Refactored Supabase Ingestion Pipeline
"""
    Skinfood Pad 고객 리뷰 → Google Sheets 연동 → Cloud SQL 'reviews' 테이블 업로드
    - 1) 제품 11개를 products 테이블에 등록 (이미 존재한다면 스킵)
    - 2) Google Sheets 로드 → 컬럼 변환/정제 및 유효성 검증
    - 3) reviews 테이블에 bulk upsert (chunk 단위)
"""

import os
import sys
import io
import re
import uuid
import hashlib
from datetime import datetime, timezone

import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ==================== 설정 ====================
TABLE_PRODUCTS = "products"
TABLE_REVIEWS = "reviews"
BATCH_SIZE = 50

# ==================== 제품 정의 ====================
SKINFOOD_PAD_PRODUCTS = {
    "아스파라거스 패드": {"id": "0f7c1538-3f79-4eba-b7ec-892ecd124622", "name": "아스파라거스 패드", "description": "", "price": 0},
    "복숭아 패드": {"id": "88ab38d5-c5fa-4b54-a62d-5a3d0cd0b270", "name": "복숭아 패드", "description": "", "price": 0},
    "블루 캐모마일 패드": {"id": "fee1ab62-21df-4890-b1f6-3d016dcbd39a", "name": "블루 캐모마일 패드", "description": "", "price": 0},
    "라이스 패드": {"id": "d0b919b1-6ddd-40a8-ae22-a21b21c11de2", "name": "라이스 패드", "description": "", "price": 0},
    "레몬그라스 패드": {"id": "1b906d7f-44b8-473a-96c4-631962ada7d0", "name": "레몬그라스 패드", "description": "", "price": 0},
    "샤인머스캣 패드": {"id": "edfb4725-3f57-45e5-aeb2-c6320634947d", "name": "샤인머스캣 패드", "description": "", "price": 0},
    "핑크자몽 패드": {"id": "e5f77ae3-b0ad-4198-b2df-a466e8a5d553", "name": "핑크자몽 패드", "description": "", "price": 0},
    "미나리 패드": {"id": "cf920939-7d95-4e2e-924f-83d64289373c", "name": "미나리 패드", "description": "", "price": 0},
    "당근 패드": {"id": "3f128ad0-7228-4f7e-8c48-f3abc894337e", "name": "당근 패드", "description": "", "price": 0},
    "감자 패드": {"id": "627e8cc4-383c-42a7-82de-a8b92b427098", "name": "감자 패드", "description": "", "price": 0},
    "도토리 패드": {"id": "d8d32744-1351-4c96-a008-b4934508f758", "name": "도토리 패드", "description": "", "price": 0},
}

TARGET_PADS = {
    "아스파라거스 패드": {"keywords": ["아스파라거스", "asparagus"],                     "default_goods": "A000000166709"},
    "복숭아 패드":       {"keywords": ["복숭아", "피치", "peach"],                       "default_goods": "A000000231714"},
    "블루 캐모마일 패드": {"keywords": ["캐모마일", "chamomile", "카모마일", "블루캐모마일"], "default_goods": "A000000166709"},
    "라이스 패드":       {"keywords": ["라이스", "rice", "쌀"],                          "default_goods": "A000000166709"},
    "레몬그라스 패드":   {"keywords": ["레몬그라스", "lemongrass"],                      "default_goods": "A000000166709"},
    "샤인머스캣 패드":   {"keywords": ["샤인머스캣", "shine", "머스캣"],                 "default_goods": "A000000166709"},
    "핑크자몽 패드":     {"keywords": ["자몽", "grapefruit", "핑크자몽"],                "default_goods": "A000000166709"},
    "미나리 패드":       {"keywords": ["미나리", "파슬리", "parsley", "판토텐산"],        "default_goods": "A000000185135"},
    "당근 패드":         {"keywords": ["당근", "캐롯", "carrot"],                        "default_goods": "A000000248098"},
    "감자 패드":         {"keywords": ["감자", "포테이토", "potato"],                    "default_goods": "A000000200396"},
    "도토리 패드":       {"keywords": ["도토리", "에이콘", "acorn"],                     "default_goods": "A000000157075"},
}

GOODS_TO_PRODUCT_ID = {
    "A000000231714": "88ab38d5-c5fa-4b54-a62d-5a3d0cd0b270",
    "A000000185135": "cf920939-7d95-4e2e-924f-83d64289373c",
    "A000000248098": "3f128ad0-7228-4f7e-8c48-f3abc894337e",
    "A000000200396": "627e8cc4-383c-42a7-82de-a8b92b427098",
    "A000000157075": "d8d32744-1351-4c96-a008-b4934508f758",
}

# ==================== 유틸 함수 ====================
def deterministic_uuid(seed_string: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed_string))

def parse_rating(raw: str) -> int:
    m = re.search(r"(\d)", str(raw))
    return int(m.group(1)) if m else 0

def parse_date(raw: str) -> str:
    cleaned = str(raw).strip()
    if not cleaned or cleaned.lower() in ("nan", "none", "null"):
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def truncate_text(text: str, max_len: int = 10000) -> str:
    text = str(text).strip()
    return text[:max_len] if len(text) > max_len else text

# [ADD] 상품코드(goods_no)와 옵션명을 통한 엄격한 product_id 매핑
def match_product_id_by_code_and_option(goods_no: str, option_name: str) -> str | None:
    goods_no = str(goods_no).strip()
    if goods_no in GOODS_TO_PRODUCT_ID:
        return GOODS_TO_PRODUCT_ID[goods_no]
    
    opt = str(option_name).lower()
    for pad_name, info in TARGET_PADS.items():
        for kw in info["keywords"]:
            if kw in opt:
                if pad_name in SKINFOOD_PAD_PRODUCTS:
                    return SKINFOOD_PAD_PRODUCTS[pad_name]["id"]
                    
    for pad_name, info in TARGET_PADS.items():
        if goods_no == info["default_goods"]:
            if pad_name in SKINFOOD_PAD_PRODUCTS:
                return SKINFOOD_PAD_PRODUCTS[pad_name]["id"]
    return None

# ==================== DB 연동 ====================
def get_connection():
    from app.api.deps import get_db_connection
    return get_db_connection()

# ==================== 제품 등록 (유지) ====================
def register_products(conn) -> None:
    now = datetime.now(timezone.utc).isoformat()
    products = []
    for _, info in SKINFOOD_PAD_PRODUCTS.items():
        products.append({
            "id": info["id"],
            "name": info["name"],
            "description": info["description"],
            "price": info["price"],
            "created_at": now,
            "updated_at": now,
        })
    cursor = conn.cursor()
    for prod in products:
        cursor.execute(
            f"""
            INSERT INTO {TABLE_PRODUCTS} (id, name, description, price, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                price = EXCLUDED.price,
                updated_at = EXCLUDED.updated_at;
            """,
            (prod["id"], prod["name"], prod["description"], prod["price"], prod["created_at"], prod["updated_at"]),
        )
    conn.commit()
    cursor.close()
    print(f"✅ 제품 {len(products)}개 upsert 완료")

# ==================== [ADD] CSV 파일 리더 구현 ====================
def load_reviews_from_csv() -> pd.DataFrame:
    csv_path = os.getenv(
        "REVIEW_CSV_PATH",
        "review_crawler/data/olive_young_reviews.csv"
    )

    if not os.path.exists(csv_path):
        print(f"[ERROR] CSV 파일이 존재하지 않습니다: {csv_path}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        print(f"[CSV] loaded_rows={len(df)} path={csv_path}")
        return df
    except Exception as e:
        print(f"[ERROR] CSV 로드 실패: {e}")
        return pd.DataFrame()

# ==================== [ADD] 데이터 전처리 및 유효성 검증 ====================
def preprocess_reviews_for_supabase(df: pd.DataFrame) -> list[dict]:
    records = []
    skipped = 0
    
    # 필수 컬럼 체크
    required_cols = {"goods_no", "option_name", "username", "skin_types", "rating", "date", "content", "review_key"}
    missing = required_cols - set(df.columns)
    if missing:
        print(f"[ERROR] 필수 컬럼 누락: {missing}")
        return []

    for idx, row in df.iterrows():
        goods_no = str(row.get("goods_no", "")).strip() if pd.notna(row.get("goods_no")) else ""
        option_name = str(row.get("option_name", "")).strip() if pd.notna(row.get("option_name")) else "단품"
        reviewer = str(row.get("username", "")).strip() if pd.notna(row.get("username")) else ""
        skin_type = str(row.get("skin_types", "")).strip() if pd.notna(row.get("skin_types")) else ""
        raw_rating = row.get("rating")
        raw_date = row.get("date", "")
        raw_content = str(row.get("content", "")).strip() if pd.notna(row.get("content")) else ""
        review_key = str(row.get("review_key", "")).strip() if pd.notna(row.get("review_key")) else ""
        
        # content가 비어 있거나 300자 미만이면 제외
        if len(raw_content) < 300:
            skipped += 1
            continue
            
        # review_key가 비어 있으면 제외
        if not review_key:
            skipped += 1
            continue
            
        # rating은 정수로 변환
        try:
            rating = int(float(raw_rating))
        except Exception:
            print(f"[WARNING] 올바르지 않은 평점 값 (행 {idx}): {raw_rating} -> 제외")
            skipped += 1
            continue
            
        # rating이 1~5 범위를 벗어나면 제외
        if rating < 1 or rating > 5:
            print(f"[WARNING] 평점 범위 초과 (행 {idx}): {rating} -> 제외")
            skipped += 1
            continue
            
        # product_id 매핑에 실패하면 제외하고 로그 출력
        product_id = match_product_id_by_code_and_option(goods_no, option_name)
        if not product_id:
            print(f"⚠️ 상품 매핑 실패 (행 {idx}): goods_no={goods_no}, option_name={option_name} -> 제외")
            skipped += 1
            continue
            
        # 날짜 변환
        review_date = parse_date(raw_date)
        
        # 피부타입 NULL 처리
        if skin_type.lower() in ("nan", "none", ""):
            skin_type = None
            
        # deterministic UUID 기반 ID 생성
        row_id = deterministic_uuid(f"skinfood:row:{goods_no}:{reviewer}:{review_date}:{idx}")
        
        # 본문 포맷팅
        full_text = f"[{goods_no}] {option_name}\n{raw_content}"
        
        record = {
            "id": row_id,
            "product_id": product_id,
            "source": "OliveYoung-OnOffline-Crawling",
            "reviewer_type": skin_type,
            "review_text": full_text,
            "rating": rating,
            "review_date": review_date,
            "sentiment": None,
            "sentiment_score": None,
            "keywords": None,
            "issue_type": None,
            "ai_summary": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "review_id": review_key,
        }
        records.append(record)
        
    print(f"[VALIDATE] valid={len(records)} skipped={skipped}")
    return records

# ==================== [ADD] 업로드 전 review_key 기준 최종 중복 제거 ====================
def deduplicate_reviews_before_upload(records: list[dict]) -> list[dict]:
    before_count = len(records)
    seen_keys = set()
    deduped = []
    for r in records:
        key = r["review_id"] # review_key가 여기 할당됨
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(r)
    print(f"[DEDUPE] before={before_count} after={len(deduped)}")
    return deduped

# ==================== [FIX] Supabase 청크 업로드 및 성공/실패 로깅 ====================
def upload_reviews_to_supabase(conn, records: list[dict]) -> None:
    total = len(records)
    success = 0
    failed = 0
    cursor = conn.cursor()
    
    for i in range(0, total, BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        values_str = ",".join(
            "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            for _ in batch
        )
        params = []
        for rec in batch:
            params.extend([
                rec["id"], rec["product_id"], rec["source"], rec["reviewer_type"], rec["review_text"],
                rec["rating"], rec["review_date"], rec["sentiment"], rec["sentiment_score"], rec["keywords"],
                rec["issue_type"], rec["ai_summary"], rec["created_at"],
            ])
            
        sql = f"""
            INSERT INTO {TABLE_REVIEWS} (
                id, product_id, source, reviewer_type, review_text,
                rating, review_date, sentiment, sentiment_score, keywords,
                issue_type, ai_summary, created_at
            ) VALUES {values_str}
            ON CONFLICT (id) DO UPDATE SET
                review_text = EXCLUDED.review_text,
                rating = EXCLUDED.rating,
                review_date = EXCLUDED.review_date,
                updated_at = NOW();
            """
        try:
            cursor.execute(sql, tuple(params))
            conn.commit()
            success += len(batch)
        except Exception as e:
            conn.rollback()
            failed += len(batch)
            print(f"[ERROR] 배치 {i//BATCH_SIZE + 1} 업로드 실패: {e}")
            
    cursor.close()
    print(f"[SUPABASE] success={success} failed={failed}")

# ==================== 실행 ====================
if __name__ == "__main__":
    conn = get_connection()
    if not conn:
        print("❌ DB 연결 실패. 종료합니다.")
        sys.exit(1)
        
    register_products(conn)
    
    # 1. CSV에서 DataFrame 로드
    df = load_reviews_from_csv()
    if not df.empty:
        # 2. 전처리 및 검증
        records = preprocess_reviews_for_supabase(df)
        if records:
            # 3. 업로드 전 중복 제거
            final_records = deduplicate_reviews_before_upload(records)
            # 4. Supabase 업로드
            upload_reviews_to_supabase(conn, final_records)
        else:
            print("⚠️ 업로드할 레코드가 전처리 결과 존재하지 않습니다.")
    else:
        print("⚠️ CSV에서 로드된 데이터가 없습니다.")
        
    conn.close()
