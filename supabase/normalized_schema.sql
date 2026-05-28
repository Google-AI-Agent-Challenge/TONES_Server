-- ========================================================== --
-- TONES 백엔드 Supabase 정규화 스크립트 (3NF)                  --
-- 설명: 기존 테이블(products, reviews, users)을 수정하지 않고  --
--       3정규형을 충족하는 신규 정규화 테이블들을 정의합니다.   --
-- ========================================================== --

-- 0. 시간 수정 트리거 함수 (갱신 시간 자동 변경용)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 1. 브랜드 마스터 테이블
CREATE TABLE IF NOT EXISTS public.normalized_brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. 상품 카테고리 마스터 테이블
CREATE TABLE IF NOT EXISTS public.normalized_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. 피부 타입 마스터 테이블 (민감성, 건성, 지성, 복합성, 수부지 등)
CREATE TABLE IF NOT EXISTS public.normalized_skin_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. 정규화된 상품 테이블
CREATE TABLE IF NOT EXISTS public.normalized_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID NOT NULL REFERENCES public.normalized_brands(id) ON DELETE RESTRICT,
    category_id UUID NOT NULL REFERENCES public.normalized_categories(id) ON DELETE RESTRICT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (price >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4.1 상품 갱신 트리거 등록
CREATE TRIGGER trigger_update_normalized_products_updated_at
    BEFORE UPDATE ON public.normalized_products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 5. 상품-피부 타입 매핑 교차 테이블 (다대다 해소용)
CREATE TABLE IF NOT EXISTS public.normalized_product_skin_types (
    product_id UUID NOT NULL REFERENCES public.normalized_products(id) ON DELETE CASCADE,
    skin_type_id UUID NOT NULL REFERENCES public.normalized_skin_types(id) ON DELETE CASCADE,
    PRIMARY KEY (product_id, skin_type_id)
);

-- 6. 리뷰 출처 마스터 테이블 (올리브영, 네이버, 쿠팡, 화해 등)
CREATE TABLE IF NOT EXISTS public.normalized_review_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 7. 정규화된 리뷰 테이블
CREATE TABLE IF NOT EXISTS public.normalized_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES public.normalized_products(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES public.normalized_review_sources(id) ON DELETE RESTRICT,
    reviewer_skin_type_id UUID REFERENCES public.normalized_skin_types(id) ON DELETE SET NULL,
    review_text TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review_date DATE NOT NULL,
    sentiment VARCHAR(20) NOT NULL CHECK (sentiment IN ('positive', 'neutral', 'negative')),
    sentiment_score NUMERIC(5, 4) CHECK (sentiment_score >= -1.0 AND sentiment_score <= 1.0),
    ai_summary TEXT,
    review_id UUID NOT NULL UNIQUE, -- 원본 외부 리뷰 고유 식별 ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 8. ABSA 감성 분석 관점 마스터 테이블 (성분/고민, 제형/발림, 용기/디자인 등)
CREATE TABLE IF NOT EXISTS public.normalized_aspects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE, -- e.g., 'ingredients', 'formulation', 'container'
    display_name VARCHAR(100) NOT NULL, -- e.g., '성분/고민', '제형/발림', '용기/디자인'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 9. 리뷰-관점별 감성 점수 매핑 테이블 (행 기반 ABSA 스코어링 테이블)
CREATE TABLE IF NOT EXISTS public.normalized_review_aspect_scores (
    review_id UUID NOT NULL REFERENCES public.normalized_reviews(id) ON DELETE CASCADE,
    aspect_id UUID NOT NULL REFERENCES public.normalized_aspects(id) ON DELETE RESTRICT,
    score NUMERIC(5, 4) NOT NULL CHECK (score >= 0.0 AND score <= 1.0),
    PRIMARY KEY (review_id, aspect_id)
);

-- 10. 리뷰 키워드 마스터 테이블
CREATE TABLE IF NOT EXISTS public.normalized_keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    word VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 11. 리뷰-키워드 다대다 매핑 테이블
CREATE TABLE IF NOT EXISTS public.normalized_review_keywords (
    review_id UUID NOT NULL REFERENCES public.normalized_reviews(id) ON DELETE CASCADE,
    keyword_id UUID NOT NULL REFERENCES public.normalized_keywords(id) ON DELETE CASCADE,
    PRIMARY KEY (review_id, keyword_id)
);

-- 12. 리뷰 이슈 타입 마스터 테이블 (트러블, 자극, 용기 불량 등)
CREATE TABLE IF NOT EXISTS public.normalized_issue_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 13. 리뷰-이슈 타입 다대다 매핑 테이블
CREATE TABLE IF NOT EXISTS public.normalized_review_issue_types (
    review_id UUID NOT NULL REFERENCES public.normalized_reviews(id) ON DELETE CASCADE,
    issue_type_id UUID NOT NULL REFERENCES public.normalized_issue_types(id) ON DELETE CASCADE,
    PRIMARY KEY (review_id, issue_type_id)
);

-- 14. 정규화된 관리자 및 사용자 테이블
CREATE TABLE IF NOT EXISTS public.normalized_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 14.1 사용자 갱신 트리거 등록
CREATE TRIGGER trigger_update_normalized_users_updated_at
    BEFORE UPDATE ON public.normalized_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========================================================== --
-- 성능 최적화를 위한 데이터베이스 인덱스 설정                      --
-- ========================================================== --

-- 상품 테이블 인덱스 (조인성능 극대화)
CREATE INDEX IF NOT EXISTS idx_normalized_products_brand ON public.normalized_products(brand_id);
CREATE INDEX IF NOT EXISTS idx_normalized_products_category ON public.normalized_products(category_id);

-- 리뷰 테이블 인덱스 (정렬 및 필터링 최적화)
CREATE INDEX IF NOT EXISTS idx_normalized_reviews_product ON public.normalized_reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_normalized_reviews_source ON public.normalized_reviews(source_id);
CREATE INDEX IF NOT EXISTS idx_normalized_reviews_date ON public.normalized_reviews(review_date DESC);
CREATE INDEX IF NOT EXISTS idx_normalized_reviews_rating ON public.normalized_reviews(rating);
CREATE INDEX IF NOT EXISTS idx_normalized_reviews_sentiment ON public.normalized_reviews(sentiment);

-- 교차 관계 테이블 탐색용 인덱스
CREATE INDEX IF NOT EXISTS idx_normalized_review_aspects_aspect ON public.normalized_review_aspect_scores(aspect_id);
CREATE INDEX IF NOT EXISTS idx_normalized_review_keywords_keyword ON public.normalized_review_keywords(keyword_id);
CREATE INDEX IF NOT EXISTS idx_normalized_review_issues_issue ON public.normalized_review_issue_types(issue_type_id);
