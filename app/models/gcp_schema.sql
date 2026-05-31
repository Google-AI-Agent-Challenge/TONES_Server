-- ========================================================== --
-- TONES GCP Cloud SQL for PostgreSQL 전용 통합 DDL 스크립트      --
-- 설명: pgvector 확장을 활성화하고, users, products, reviews,   --
--       user_layouts 테이블 및 HNSW 코사인 유사도 벡터 인덱스를   --
--       단일 데이터베이스 내에 통합 구성합니다.                --
-- ========================================================== --

-- 1. pgvector 확장 모듈 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. updated_at 자동 갱신을 위한 공용 함수 정의
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 3. Users 테이블 생성
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

DROP TRIGGER IF EXISTS update_users_updated_at ON public.users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 4. Products 테이블 생성
CREATE TABLE IF NOT EXISTS public.products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_name TEXT,  -- 정규화 스키마 호환성 보완용 브랜드 필드
    product_name TEXT, -- 정규화 스키마 호환성 보완용 상품명 필드
    name TEXT NOT NULL,
    description TEXT,
    price NUMERIC,
    category TEXT DEFAULT 'pad',
    target_skin TEXT,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

DROP TRIGGER IF EXISTS update_products_updated_at ON public.products;
CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON public.products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 5. 감성 판단을 위한 ENUM 타입 선언
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sentiment_type') THEN
        CREATE TYPE sentiment_type AS ENUM ('positive', 'neutral', 'negative');
    END IF;
END$$;

-- 6. Reviews 테이블 생성 (임베딩 pgvector 통합 컬럼 포함)
CREATE TABLE IF NOT EXISTS public.reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    reviewer_type TEXT,
    review_text TEXT NOT NULL,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review_date DATE NOT NULL DEFAULT CURRENT_DATE,
    sentiment sentiment_type NOT NULL,
    sentiment_score NUMERIC,
    keywords TEXT[] NOT NULL DEFAULT '{}',
    issue_type TEXT,
    ai_summary TEXT,
    review_id UUID UNIQUE,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    
    -- pgvector 768차원 임베딩 컬럼 통합 (Pinecone 대체)
    embedding vector(768),
    
    -- 감성 속성 점수 보완 컬럼
    score_ingredients NUMERIC DEFAULT 0.5,
    score_formulation NUMERIC DEFAULT 0.5,
    score_container NUMERIC DEFAULT 0.5
);

-- 7. RAG 초고속 검색을 위한 pgvector HNSW 코사인 유사도 인덱스 생성
CREATE INDEX IF NOT EXISTS reviews_embedding_hnsw_idx 
ON public.reviews USING hnsw (embedding vector_cosine_ops);

-- 8. User Layouts 테이블 생성 (Phase 1 레이아웃 일원화 지원)
CREATE TABLE IF NOT EXISTS public.user_layouts (
    user_token TEXT PRIMARY KEY,
    pinned_widget TEXT,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

DROP TRIGGER IF EXISTS update_user_layouts_updated_at ON public.user_layouts;
CREATE TRIGGER update_user_layouts_updated_at BEFORE UPDATE ON public.user_layouts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================================== --
-- 기초 대시보드 Products 시드 데이터 로딩                     --
-- ========================================================== --
INSERT INTO public.products (id, name, brand_name, product_name, description, price, category, target_skin, created_at, updated_at) VALUES 
('e680f731-cfde-427f-9077-62f7e484ec21', '1025 독도 패드', '라운드랩', '1025 독도 패드', '울릉도 해양심층수의 풍부한 미네랄로 피부를 순하고 촉촉하게 가꿔주는 저자극 수분 듀오 세트', 32000, 'pad', '민감성', now() - interval '34 days', now()),
('04472697-d7c5-4cbe-bbc1-3cb62d3d4eba', '캐롯 카로틴 카밍 워터 패드 (당근 패드)', '스킨푸드', '캐롯 카로틴 카밍 워터 패드 (당근 패드)', '제주산 티트리 추출물을 가득 머금어 트러블 부위를 빠르게 진정시키고 각질을 케어하는 비건 인증 패드', 22000, 'pad', '민감성 및 자극성', now() - interval '45 days', now()),
('63d4efec-06f6-43d2-93b4-11b26b88c9e3', '티트리 트러블 패드', '메디힐', '티트리 트러블 패드', '고농축 병풀 추출물(CICA)과 마데카소사이드 성분이 붉어지고 예민해진 피부를 빠르게 진정시키는 카밍 에센스', 24000, 'pad', '지성 및 여드름성', now() - interval '42 days', now()),
('cda7adcd-30e5-4610-8dd6-d1b48a3e018a', '5번 글루타치온 필름 패드', '넘버즈인', '5번 글루타치온 필름 패드', '눈시림 없이 온 가족이 사용할 수 있는 백탁 없는 순한 데일리 물리적 자외선 차단제', 19800, 'pad', '칙칙한 피부', now() - interval '23 days', now())
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    brand_name = EXCLUDED.brand_name,
    product_name = EXCLUDED.product_name,
    description = EXCLUDED.description,
    price = EXCLUDED.price,
    category = EXCLUDED.category,
    target_skin = EXCLUDED.target_skin,
    updated_at = now();
