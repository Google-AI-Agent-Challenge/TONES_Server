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
import gspread
from google.oauth2.service_account import Credentials

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ==================== 설정 ====================
TABLE_PRODUCTS = "products"
TABLE_REVIEWS = "reviews"
BATCH_SIZE = 50

# Google Sheets configuration (set via environment variables)
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_WORKSHEET_NAME = os.getenv("GOOGLE_WORKSHEET_NAME", "Sheet1")

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
    "당근 패드": {"id": "627e8cc4-383c-42a7-82de-a8b92b427098", "name": "당근 패드", "description": "", "price": 0},
    "감자 패드": {"id": "3f128ad0-7228-4f7e-8c48-f3abc894337e", "name": "감자 패드", "description": "", "price": 0},
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
    "A000000248098": "627e8cc4-383c-42a7-82de-a8b92b427098",
    "A000000200396": "3f128ad0-7228-4f7e-8c48-f3abc894337e",
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
    from app.database.connection import get_db_connection
    return get_db_connection()

# ==================== 제품 등록 (유지) ====================
def register_products(conn) -> None:
    print("ℹ️ Products are already seeded in the database via gcp_schema.sql. Skipping register_products.")

# ==================== [ADD] Google Sheets 리더 구현 ====================
def load_reviews_from_google_sheet() -> pd.DataFrame:
    if not GOOGLE_SERVICE_ACCOUNT_FILE or not GOOGLE_SHEET_ID:
        print("[ERROR] GOOGLE_SERVICE_ACCOUNT_FILE 또는 GOOGLE_SHEET_ID 환경변수가 설정되지 않았습니다.")
        return pd.DataFrame()
        
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_FILE, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet(GOOGLE_WORKSHEET_NAME)
        data = sheet.get_all_values()
        if not data:
            print("[SHEET] 시트가 비어 있습니다.")
            return pd.DataFrame()
            
        headers = data[0]
        rows = data[1:]
        return pd.DataFrame(rows, columns=headers)
    except Exception as e:
        print(f"[ERROR] Google Sheets 로드 오류: {e}")
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
        goods_no = str(row.get("goods_no", "")).strip()
        option_name = str(row.get("option_name", "")).strip()
        reviewer = str(row.get("username", "")).strip()
        skin_type = str(row.get("skin_types", "")).strip()
        raw_rating = row.get("rating", "5")
        raw_date = row.get("date", "")
        raw_content = row.get("content", "")
        review_key = str(row.get("review_key", "")).strip()
        
        # 1. rating 범위 검증 및 정수 변환
        try:
            rating = int(raw_rating)
            if rating < 1 or rating > 5:
                rating = 5
        except Exception:
            rating = 5
            
        # 2. 날짜 변환
        review_date = parse_date(raw_date)
        
        # 3. 본문 누락 검증
        review_text_raw = truncate_text(raw_content)
        if not review_text_raw:
            skipped += 1
            continue
            
        # 4. product_id 매핑 누락 검증
        product_id = match_product_id_by_code_and_option(goods_no, option_name)
        if not product_id:
            skipped += 1
            print(f"⚠️ 상품 매핑 실패 (행 {idx}): goods_no={goods_no}, option_name={option_name} -> 건너뜀")
            continue
            
        # 피부타입 NULL 처리
        if skin_type.lower() in ("nan", "none", ""):
            skin_type = None
            
        # [FIX] deterministic UUID 기반 ID 생성
        row_id = deterministic_uuid(f"skinfood:row:{goods_no}:{reviewer}:{review_date}:{idx}")
        
        # 본문 포맷팅
        full_text = f"[{goods_no}] {option_name}\n{review_text_raw}"
        
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
        
    print(f"✅ 전처리 및 검증 완료: {len(records)}개 성공, {skipped}개 스킵")
    return records

# ==================== [ADD] 업로드 전 review_key 기준 최종 중복 제거 ====================
def deduplicate_reviews_before_upload(records: list[dict]) -> list[dict]:
    seen_keys = set()
    deduped = []
    for r in records:
        key = r["review_id"] # review_key가 여기 할당됨
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(r)
    print(f"✅ 최종 업로드 대상 (중복 제거 후): {len(deduped)}개")
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
    import argparse
    parser = argparse.ArgumentParser(description="Upload Olive Young reviews to GCP Cloud SQL")
    parser.add_argument("--file", type=str, default="review_crawler/data/olive_young_reviews.csv", help="Local CSV file path")
    parser.add_argument("--use-google-sheets", action="store_true", help="Use Google Sheets instead of local CSV")
    args = parser.parse_args()

    conn = get_connection()
    if not conn:
        print("❌ DB 연결 실패. 종료합니다.")
        sys.exit(1)
        
    register_products(conn)
    
    df = pd.DataFrame()
    if args.use_google_sheets:
        print("🌐 Google Sheets에서 데이터를 로드합니다...")
        df = load_reviews_from_google_sheet()
    else:
        file_path = args.file
        print(f"📄 로컬 CSV 파일에서 데이터를 로드합니다: {file_path}")
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path, encoding="utf-8-sig")
            except Exception as e:
                print(f"[ERROR] CSV 파일 읽기 실패: {e}")
        else:
            print(f"❌ 파일을 찾을 수 없습니다: {file_path}")

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
        print("⚠️ 로드된 데이터가 없습니다.")
        
    conn.close()
