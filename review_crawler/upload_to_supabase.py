# -*- coding: utf-8 -*-
"""
    Skinfood Pad 고객 리뷰 → Cloud SQL 'reviews' 테이블 업로드
    - 1) 제품 11개를 products 테이블에 등록 (이미 존재한다면 스킵)
    - 2) XLSX 파일 로드 → 컬럼 변환/정제
    - 3) product_id 매핑 후 reviews 테이블에 bulk upsert
"""

import os
import sys
import io
import re
import uuid
from datetime import datetime, timezone

import pandas as pd
# Google Sheets API imports
import gspread
from google.oauth2.service_account import Credentials

# Adjust stdout encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ==================== 설정 ====================
XLSX_PATH = os.path.join(os.path.dirname(__file__), "스킨푸드_패드_고객리뷰.xlsx")  # fallback path
TABLE_PRODUCTS = "products"
TABLE_REVIEWS = "reviews"
BATCH_SIZE = 50

# Google Sheets configuration (set via environment variables)
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")  # Spreadsheet ID
GOOGLE_SHEETS_RANGE = os.getenv("GOOGLE_SHEETS_RANGE", "A1:Z")  # Range to fetch
GOOGLE_SHEETS_CRED_FILE = os.getenv("GOOGLE_SHEETS_CRED_FILE")  # Path to service account JSON

# ==================== 유틸 함수 ====================
def deterministic_uuid(seed_string: str) -> str:
    """재실행 시 동일한 UUID를 생성하여 중복 삽입을 방지합니다."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed_string))

def parse_rating(raw: str) -> int:
    """'5점' → 5"""
    m = re.search(r"(\d)", str(raw))
    return int(m.group(1)) if m else 0

def parse_date(raw: str) -> str:
    """'2026.04.10' → '2026-04-10'"""
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

def match_product_id(target_name: str) -> str | None:
    """타겟상품명에서 제품 키워드를 추출해 product_id를 매핑합니다."""
    target = str(target_name).strip()
    for keyword, info in SKINFOOD_PAD_PRODUCTS.items():
        if keyword in target:
            return info["id"]
    return None

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

# ==================== DB 연동 ====================
def get_connection():
    """FastAPI deps에서 정의된 DB 커넥션 로직을 재사용한다."""
    from app.api.deps import get_db_connection
    return get_db_connection()

# ==================== 제품 등록 ====================
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

# ==================== 데이터 변환 ====================
def load_and_transform() -> list[dict]:
    # Load data from Google Sheets; fallback to local Excel if sheet config missing
    if GOOGLE_SHEETS_ID and GOOGLE_SHEETS_CRED_FILE:
        print(f"📂 구글 시트 로딩: ID={GOOGLE_SHEETS_ID}, RANGE={GOOGLE_SHEETS_RANGE}")
        creds = Credentials.from_service_account_file(GOOGLE_SHEETS_CRED_FILE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEETS_ID).worksheet('Sheet1')
        data = sheet.get(GOOGLE_SHEETS_RANGE)
        # First row assumed header
        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)
    else:
        print(f"📂 엑셀 파일 로딩 (fallback): {XLSX_PATH}")
        df = pd.read_excel(XLSX_PATH)
    records = []
    skipped = 0
    for idx, row in df.iterrows():
        product_name = str(row.get("타겟상품명", "")).strip()
        product_code = str(row.get("올리브영 상품코드", "")).strip()
        option_name = str(row.get("구매 옵션명", "")).strip()
        reviewer = str(row.get("작성자", "")).strip()
        skin_type = str(row.get("피부타입", "")).strip()
        rating = parse_rating(row.get("별점", "0"))
        review_date = parse_date(row.get("작성일", ""))
        review_text = truncate_text(row.get("리뷰 내용", ""))
        product_id = match_product_id(product_name)
        if not product_id:
            skipped += 1
            print(f"⚠️  제품 매핑 실패 (행 {idx}): '{product_name}' → 건너뜀")
            continue
        if skin_type.lower() == "nan" or not skin_type:
            skin_type = None
        row_id = deterministic_uuid(f"skinfood:row:{product_code}:{reviewer}:{review_date}:{idx}")
        review_id = deterministic_uuid(f"skinfood:review:{product_code}:{reviewer}:{review_date}:{idx}")
        record = {
            "id": row_id,
            "product_id": product_id,
            "source": "OliveYoung-OnOffline-Crawling",
            "reviewer_type": skin_type,
            "review_text": f"[{product_name}] {option_name}\n{review_text}",
            "rating": rating,
            "review_date": review_date,
            "sentiment": None,
            "sentiment_score": None,
            "keywords": None,
            "issue_type": None,
            "ai_summary": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "review_id": review_id,
        }
        records.append(record)
    print(f"✅ 변환 완료: {len(records)}개 레코드, 건너뜀 {skipped}개")
    return records

# ==================== 리뷰 업로드 ====================
def upload_reviews(conn, records: list[dict]) -> None:
    total = len(records)
    success = 0
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
        cursor.execute(sql, tuple(params))
        conn.commit()
        success += len(batch)
        print(f"🚀 배치 {i//BATCH_SIZE + 1}: {len(batch)}개 upsert 완료")
    cursor.close()
    print(f"📊 업로드 요약: 전체 {total}, 성공 {success}")

# ==================== 실행 ====================
if __name__ == "__main__":
    conn = get_connection()
    if not conn:
        print("❌ DB 연결 실패. 종료.")
        sys.exit(1)
    register_products(conn)
    records = load_and_transform()
    if records:
        upload_reviews(conn, records)
    else:
        print("⚠️  업로드할 레코드가 없습니다.")
    conn.close()
