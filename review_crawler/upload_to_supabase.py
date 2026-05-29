# -*- coding: utf-8 -*-
"""
┌──────────────────────────────────────────────────────────┐
│ 스킨푸드 패드 고객 리뷰 → Supabase 'reviews' 테이블 업로드 │
│                                                          │
│ 1. 스킨푸드 패드 제품 11개를 products 테이블에 등록        │
│ 2. XLSX 파일 로드 → 컬럼 변환/정제                       │
│ 3. product_id 매핑 후 reviews 테이블에 bulk upsert        │
└──────────────────────────────────────────────────────────┘
"""

import os
import sys
import io
import re
import uuid
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# ─── UTF-8 stdout ───────────────────────────────────────────
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ─── 설정 ──────────────────────────────────────────────────
XLSX_PATH = os.path.join(os.path.dirname(__file__), "스킨푸드_패드_고객리뷰.xlsx")
TABLE_PRODUCTS = "products"
TABLE_REVIEWS  = "reviews"
BATCH_SIZE     = 50

# ─── 환경 변수 로드 ────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

# ─── Supabase 클라이언트 초기화 ────────────────────────────
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print(f"✅ Supabase 연결 완료: {SUPABASE_URL}")


# ╔═══════════════════════════════════════════════════════════╗
# ║ 스킨푸드 패드 제품 정의 (11종 DB ID 매핑)                 ║
# ╚═══════════════════════════════════════════════════════════╝

SKINFOOD_PAD_PRODUCTS = {
    "아스파라거스 패드": {"id": "0f7c1538-3f79-4eba-b7ec-892ecd124622"},
    "복숭아 패드":       {"id": "88ab38d5-c5fa-4b54-a62d-5a3d0cd0b270"},
    "블루 캐모마일 패드": {"id": "fee1ab62-21df-4890-b1f6-3d016dcbd39a"},
    "라이스 패드":       {"id": "d0b919b1-6ddd-40a8-ae22-a21b21c11de2"},
    "레몬그라스 패드":   {"id": "1b906d7f-44b8-473a-96c4-631962ada7d0"},
    "샤인머스캣 패드":   {"id": "edfb4725-3f57-45e5-aeb2-c6320634947d"},
    "핑크자몽 패드":     {"id": "e5f77ae3-b0ad-4198-b2df-a466e8a5d553"},
    "미나리 패드":       {"id": "cf920939-7d95-4e2e-924f-83d64289373c"},
    "당근 패드":         {"id": "3f128ad0-7228-4f7e-8c48-f3abc894337e"},
    "감자 패드":         {"id": "627e8cc4-383c-42a7-82de-a8b92b427098"},
    "도토리 패드":       {"id": "d8d32744-1351-4c96-a008-b4934508f758"},
}


# ╔═══════════════════════════════════════════════════════════╗
# ║ 유틸리티 함수들                                           ║
# ╚═══════════════════════════════════════════════════════════╝

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


# ╔═══════════════════════════════════════════════════════════╗
# ║ Step 1: products 테이블에 스킨푸드 패드 등록              ║
# ╚═══════════════════════════════════════════════════════════╝

def register_products() -> None:
    """11개 스킨푸드 패드 제품을 products 테이블에 upsert합니다."""
    now = datetime.now(timezone.utc).isoformat()
    products = []

    for keyword, info in SKINFOOD_PAD_PRODUCTS.items():
        products.append({
            "id":          info["id"],
            "name":        info["name"],
            "description": info["description"],
            "price":       info["price"],
            "created_at":  now,
            "updated_at":  now,
        })

    print(f"\n📦 products 테이블에 {len(products)}개 스킨푸드 패드 제품 등록 중...")

    try:
        response = (
            supabase.table(TABLE_PRODUCTS)
            .upsert(products, on_conflict="id")
            .execute()
        )
        inserted = len(response.data) if response.data else 0
        print(f"   ✅ {inserted}개 제품 upsert 완료")
    except Exception as e:
        print(f"   ❌ 제품 등록 오류: {e}")
        sys.exit(1)


# ╔═══════════════════════════════════════════════════════════╗
# ║ Step 2: XLSX 로드 → 변환                                ║
# ╚═══════════════════════════════════════════════════════════╝

def load_and_transform() -> list[dict]:
    """XLSX를 로드하고 reviews 테이블 스키마로 변환합니다."""
    print(f"\n📂 엑셀 파일 로딩: {XLSX_PATH}")
    df = pd.read_excel(XLSX_PATH)
    print(f"   → {len(df)}개 행 로드 완료")

    records = []
    skipped = 0

    for idx, row in df.iterrows():
        product_name = str(row.get("타겟상품명", "")).strip()
        product_code = str(row.get("올리브영 상품코드", "")).strip()
        option_name  = str(row.get("구매 옵션명", "")).strip()
        reviewer     = str(row.get("작성자", "")).strip()
        skin_type    = str(row.get("피부타입", "")).strip()
        rating       = parse_rating(row.get("별점", "0"))
        review_date  = parse_date(row.get("작성일", ""))
        review_text  = truncate_text(row.get("리뷰 내용", ""))

        # product_id 매핑
        product_id = match_product_id(product_name)
        if not product_id:
            skipped += 1
            print(f"   ⚠️  제품 매핑 실패 (행 {idx}): '{product_name}' → 건너뜀")
            continue

        # nan 처리
        if skin_type.lower() == "nan" or not skin_type:
            skin_type = None

        # 고유 ID 생성 (deterministic)
        row_id    = deterministic_uuid(f"skinfood:row:{product_code}:{reviewer}:{review_date}:{idx}")
        review_id = deterministic_uuid(f"skinfood:review:{product_code}:{reviewer}:{review_date}:{idx}")

        record = {
            "id":              row_id,
            "product_id":      product_id,
            "source":          "OliveYoung-OnOffline-Crawling",
            "reviewer_type":   skin_type,
            "review_text":     f"[{product_name}] {option_name}\n{review_text}",
            "rating":          rating,
            "review_date":     review_date,
            "sentiment":       None,
            "sentiment_score": None,
            "keywords":        None,
            "issue_type":      None,
            "ai_summary":      None,
            "created_at":      datetime.now(timezone.utc).isoformat(),
            "review_id":       review_id,
        }
        records.append(record)

    print(f"   → {len(records)}개 레코드 변환 완료 (건너뜀: {skipped}개)")
    return records


# ╔═══════════════════════════════════════════════════════════╗
# ║ Step 3: Supabase reviews 테이블 업로드                   ║
# ╚═══════════════════════════════════════════════════════════╝

def upload_reviews(records: list[dict]) -> None:
    """reviews 테이블에 배치 단위로 upsert합니다."""
    total = len(records)
    success_count = 0
    error_count = 0

    print(f"\n🚀 Supabase 업로드 시작 (총 {total}개, 배치 {BATCH_SIZE}개씩)")
    print("─" * 60)

    for i in range(0, total, BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        batch_end = min(i + BATCH_SIZE, total)

        try:
            response = (
                supabase.table(TABLE_REVIEWS)
                .upsert(batch, on_conflict="id")
                .execute()
            )
            inserted = len(response.data) if response.data else 0
            success_count += inserted
            print(f"   ✅ 배치 {batch_num}: {i+1}~{batch_end} → {inserted}개 upsert 성공")

        except Exception as e:
            error_count += len(batch)
            print(f"   ❌ 배치 {batch_num}: {i+1}~{batch_end} → 오류: {e}")

    print("─" * 60)
    print(f"\n📊 업로드 결과 요약")
    print(f"   • 전체:  {total}개")
    print(f"   • 성공:  {success_count}개")
    print(f"   • 실패:  {error_count}개")

    if error_count == 0:
        print("\n🎉 모든 리뷰 데이터가 Supabase에 성공적으로 저장되었습니다!")
    else:
        print(f"\n⚠️  {error_count}개 레코드 업로드에 실패했습니다.")


# ╔═══════════════════════════════════════════════════════════╗
# ║ 실행                                                     ║
# ╚═══════════════════════════════════════════════════════════╝

if __name__ == "__main__":
    print("=" * 60)
    print("  스킨푸드 패드 리뷰 → Supabase 업로더 v2")
    print("=" * 60)

    # 1) 제품 등록 (이미 등록되어 있으므로 생략)
    # register_products()

    # 2) 리뷰 변환
    records = load_and_transform()

    # 3) 리뷰 업로드
    if records:
        upload_reviews(records)
    else:
        print("\n⚠️  업로드할 레코드가 없습니다.")
