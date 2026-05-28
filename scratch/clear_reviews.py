# -*- coding: utf-8 -*-
"""
Supabase 'reviews' 테이블 및 Pinecone 벡터 DB 초기화 스크립트
"""

import os
from dotenv import load_dotenv
from supabase import create_client

# 환경변수 로드
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ 에러: Supabase 환경 변수가 설정되지 않았습니다.")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def clear_reviews_table():
    print("=" * 60)
    print("      Supabase 'reviews' 테이블 전체 초기화 및 비우기")
    print("=" * 60)
    
    try:
        # Supabase에서는 안전을 위해 delete().neq() 또는 delete().gt()로 전체 행을 타겟팅하여 삭제합니다.
        # id가 빈 UUID가 아닌 모든 행을 지우도록 처리합니다.
        print("[*] reviews 테이블의 기존 행들을 삭제하는 중입니다...")
        response = (
            supabase.table("reviews")
            .delete()
            .neq("id", "00000000-0000-0000-0000-000000000000")
            .execute()
        )
        deleted_count = len(response.data) if response.data else 0
        print(f"✅ 완료: 총 {deleted_count}개의 리뷰 레코드가 Supabase에서 제거되었습니다.")
        
    except Exception as e:
        print(f"❌ Supabase 테이블 비우기 중 에러 발생: {e}")
        print("\n💡 팁: 만약 권한 거부(RLS) 등이 발생한다면, Supabase 대시보드의 [SQL Editor]에서")
        print("   TRUNCATE TABLE reviews CASCADE; 명령어를 직접 실행하시는 것이 가장 확실합니다.")

if __name__ == "__main__":
    confirm = input("⚠️  정말로 'reviews' 테이블의 모든 데이터를 삭제하시겠습니까? (yes/no): ")
    if confirm.lower() == "yes":
        clear_reviews_table()
    else:
        print("❌ 작업이 취소되었습니다.")
