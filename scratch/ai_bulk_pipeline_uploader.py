# -*- coding: utf-8 -*-
"""
실제 크롤링된 리뷰 엑셀 데이터를 로컬 FastAPI AI 파이프라인(/reviews/bulk)에 업로드하는 스크립트.
이 스크립트를 통해 업로드하면:
1. 각 리뷰에 대해 Gemini 2.0-flash ABSA(다중 감성 분석)가 실행됩니다.
2. Pinecone 벡터 DB에 768차원 임베딩 벡터로 자동 분산 적재됩니다.
3. Supabase DB에 AI 속성 만족도 점수가 완벽하게 채워진 채 최종 저장됩니다.
"""

import os
import re
import uuid
import pandas as pd
import requests
from dotenv import load_dotenv

# 설정
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
XLSX_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "스킨푸드_패드_고객리뷰.xlsx")
API_URL = "http://localhost:8000/api/v1/dashboard/reviews/bulk"

# 스킨푸드 패드 11종 제품 고유 ID 매핑 (deterministic)
SKINFOOD_PAD_PRODUCTS = {
    "아스파라거스 패드": "skinfood:아스파라거스 패드",
    "복숭아 패드": "skinfood:복숭아 패드",
    "블루 캐모마일 패드": "skinfood:블루 캐모마일 패드",
    "라이스 패드": "skinfood:라이스 패드",
    "레몬그라스 패드": "skinfood:레몬그라스 패드",
    "샤인머스캣 패드": "skinfood:샤인머스캣 패드",
    "핑크자몽 패드": "skinfood:핑크자몽 패드",
    "미나리 패드": "skinfood:미나리 패드",
    "당근 패드": "skinfood:당근 패드",
    "감자 패드": "skinfood:감자 패드",
    "도토리 패드": "skinfood:도토리 패드",
}

def get_product_id(pad_name: str) -> str:
    for keyword, seed in SKINFOOD_PAD_PRODUCTS.items():
        if keyword in pad_name:
            return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))
    return str(uuid.uuid4())

def parse_rating(raw: str) -> int:
    m = re.search(r"(\d)", str(raw))
    return int(m.group(1)) if m else 0

def parse_date(raw: str) -> str:
    cleaned = str(raw).strip()
    for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            from datetime import datetime
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return cleaned

def upload_via_ai_pipeline():
    if not os.path.exists(XLSX_PATH):
        print(f"❌ 에러: 엑셀 파일이 존재하지 않습니다. 경로: {XLSX_PATH}")
        return

    print("=" * 60)
    print("      올리브영 실시간 크롤링 리뷰 → AI 파이프라인 업로더")
    print("=" * 60)
    
    print(f"[*] 엑셀 파일 로드 중: {XLSX_PATH}")
    df = pd.read_excel(XLSX_PATH)
    print(f"✅ 로드 완료: 총 {len(df)}개의 행 감지")

    # FastAPI 서버 구동 확인
    try:
        requests.get("http://localhost:8000/health", timeout=3)
    except Exception:
        print("❌ 에러: 로컬 FastAPI 백엔드 서버(http://localhost:8000)가 켜져 있지 않습니다.")
        print("   먼저 uvicorn app.main:app --reload --port 8000 명령어로 서버를 구동해 주세요.")
        return

    payload_reviews = []
    for idx, row in df.iterrows():
        product_name = str(row.get("타겟상품명", "")).strip()
        product_id = get_product_id(product_name)
        rating = parse_rating(row.get("별점", "0"))
        review_date = parse_date(row.get("작성일", ""))
        content = str(row.get("리뷰 내용", "")).strip()
        skin_type = str(row.get("피부타입", "")).strip()
        if skin_type.lower() == "nan" or not skin_type:
            skin_type = None
            
        reviewer = str(row.get("작성자", "")).strip()
        goods_code = str(row.get("올리브영 상품코드", "")).strip()
        
        # 고유 deterministic review_id 생성
        review_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"skinfood:review:{goods_code}:{reviewer}:{review_date}:{idx}"))

        payload_reviews.append({
            "review_id": review_id,
            "product_id": product_id,
            "content": content,
            "rating": rating,
            "review_date": review_date,
            "source": "올리브영 온/오프라인",
            "reviewer_type": skin_type
        })

    total_count = len(payload_reviews)
    print(f"[*] AI 파이프라인으로 전송할 데이터를 조립 완료했습니다. (총 {total_count}건)")
    print("[*] Gemini ABSA 감성 분석 및 Pinecone 벡터 DB 적재 처리를 위해 전송을 시작합니다...")
    
    # AI 호출 속도를 고려하여 5개씩 나누어 전송 (FastAPI에서 비동기로 다수 AI API를 호출하므로 과도한 부하 방지)
    batch_size = 5
    success_count = 0
    
    for i in range(0, total_count, batch_size):
        batch = payload_reviews[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        batch_end = min(i + batch_size, total_count)
        
        print(f"🚀 [배치 {batch_num}] {i+1}~{batch_end}번째 리뷰 업로드 및 AI 분석 진행 중...")
        try:
            # FastAPI bulk API 엔드포인트 호출
            res = requests.post(API_URL, json=batch, timeout=120)
            if res.status_code == 201:
                data = res.json()
                success = data.get("success_count", 0)
                success_count += success
                print(f"   ✅ [배치 {batch_num}] 성공: {success}건 분석 및 적재 완료 (누적: {success_count}건)")
            else:
                print(f"   ❌ [배치 {batch_num}] 전송 실패 (상태 코드 {res.status_code}): {res.text}")
        except Exception as e:
            print(f"   ❌ [배치 {batch_num}] 전송 실패 (서버 오류): {e}")

    print("=" * 60)
    print("      🎉 AI 파이프라인 업로드 작업 완료!")
    print(f"      • 대상 데이터: {total_count}건")
    print(f"      • 파이프라인 적재 성공: {success_count}건")
    print("=" * 60)

if __name__ == "__main__":
    confirm = input("⚠️  FastAPI AI 파이프라인을 구동하여 엑셀의 리뷰 데이터를 분석 적재하시겠습니까? (yes/no): ")
    if confirm.lower() == "yes":
        upload_via_ai_pipeline()
    else:
        print("❌ 작업이 취소되었습니다.")
