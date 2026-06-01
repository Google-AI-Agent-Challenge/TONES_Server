-- ========================================================== --
-- TONES GCP Cloud SQL for PostgreSQL 전용 통합 DDL 스크립트      --
-- 설명: pgvector 확장을 활성화하고, 정규화(3NF)된 구조의        --
--       users, brands, categories, skin_types, products,      --
--       keywords, reviews, review_keywords, user_layouts      --
--       테이블을 단일 데이터베이스 내에 통합 구성합니다.          --
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

-- 3. ENUM 타입 선언
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sentiment_type') THEN
        CREATE TYPE sentiment_type AS ENUM ('positive', 'neutral', 'negative');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'source_type') THEN
        CREATE TYPE source_type AS ENUM ('youtube', 'blog', 'naver_store', 'olive_young', 'mock', 'other');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reviewer_type') THEN
        CREATE TYPE reviewer_type AS ENUM ('general', 'influencer', 'expert');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'issue_type') THEN
        CREATE TYPE issue_type AS ENUM ('ingredients', 'formulation', 'container', 'scent', 'irritation', 'none', 'other');
    END IF;
END$$;

-- 4. Users 테이블 생성
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

DROP TRIGGER IF EXISTS update_users_updated_at ON public.users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 5. Lookup 테이블 생성
-- 5-1. BRANDS
CREATE TABLE IF NOT EXISTS public.brands (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL
);

-- 5-2. CATEGORIES
CREATE TABLE IF NOT EXISTS public.categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

-- 5-3. SKIN_TYPES
CREATE TABLE IF NOT EXISTS public.skin_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

-- 5-4. KEYWORDS
CREATE TABLE IF NOT EXISTS public.keywords (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(100) UNIQUE NOT NULL
);

-- 6. Products 테이블 생성 (정규화 스키마 반영)
CREATE TABLE IF NOT EXISTS public.products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id INT NOT NULL REFERENCES public.brands(id) ON DELETE RESTRICT,
    product_name VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC,
    category_id INT NOT NULL REFERENCES public.categories(id) ON DELETE RESTRICT,
    skin_type_id INT NOT NULL REFERENCES public.skin_types(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

DROP TRIGGER IF EXISTS update_products_updated_at ON public.products;
CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON public.products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 7. Reviews 테이블 생성 (정규화 스키마 반영)
CREATE TABLE IF NOT EXISTS public.reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    source source_type NOT NULL,
    reviewer_type reviewer_type NOT NULL,
    review_text TEXT NOT NULL,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review_date DATE NOT NULL DEFAULT CURRENT_DATE,
    sentiment sentiment_type NOT NULL,
    sentiment_score NUMERIC NOT NULL,
    issue_type issue_type NOT NULL,
    ai_summary TEXT NOT NULL,
    embedding vector(768),
    score_ingredients NUMERIC DEFAULT 0.5,
    score_formulation NUMERIC DEFAULT 0.5,
    score_container NUMERIC DEFAULT 0.5,
    review_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

-- 8. REVIEW_KEYWORDS 다대다 중간 테이블 생성
CREATE TABLE IF NOT EXISTS public.review_keywords (
    review_id UUID NOT NULL REFERENCES public.reviews(id) ON DELETE CASCADE,
    keyword_id INT NOT NULL REFERENCES public.keywords(id) ON DELETE CASCADE,
    PRIMARY KEY (review_id, keyword_id)
);

-- 9. pgvector RAG 초고속 검색 인덱스 생성
CREATE INDEX IF NOT EXISTS reviews_embedding_hnsw_idx 
ON public.reviews USING hnsw (embedding vector_cosine_ops);

-- 10. User Layouts 테이블 생성
CREATE TABLE IF NOT EXISTS public.user_layouts (
    user_token TEXT PRIMARY KEY,
    pinned_widget TEXT,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

DROP TRIGGER IF EXISTS update_user_layouts_updated_at ON public.user_layouts;
CREATE TRIGGER update_user_layouts_updated_at BEFORE UPDATE ON public.user_layouts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ========================================================== --
-- 기초 대시보드 및 정규화 시드 데이터 로딩                      --
-- ========================================================== --

-- 1. Lookup 테이블 시드 데이터 로드
INSERT INTO public.brands (name) VALUES 
('라운드랩'), ('스킨푸드'), ('메디힐'), ('넘버즈인')
ON CONFLICT (name) DO NOTHING;

INSERT INTO public.categories (name) VALUES 
('pad')
ON CONFLICT (name) DO NOTHING;

INSERT INTO public.skin_types (name) VALUES 
('민감성'), ('민감성 및 자극성'), ('지성 및 여드름성'), ('칙칙한 피부')
ON CONFLICT (name) DO NOTHING;

-- 2. Products 테이블 시드 데이터 로드 (Lookup 매핑 포함)
INSERT INTO public.products (id, brand_id, product_name, description, price, category_id, skin_type_id, created_at, updated_at) VALUES 
(
    'e680f731-cfde-427f-9077-62f7e484ec21', 
    (SELECT id FROM public.brands WHERE name = '라운드랩'), 
    '1025 독도 패드', 
    '울릉도 해양심층수의 풍부한 미네랄로 피부를 순하고 촉촉하게 가꿔주는 저자극 수분 듀오 세트', 
    32000, 
    (SELECT id FROM public.categories WHERE name = 'pad'), 
    (SELECT id FROM public.skin_types WHERE name = '민감성'), 
    now() - interval '34 days', 
    now()
),
(
    '04472697-d7c5-4cbe-bbc1-3cb62d3d4eba', 
    (SELECT id FROM public.brands WHERE name = '스킨푸드'), 
    '캐롯 카로틴 카밍 워터 패드 (당근 패드)', 
    '제주산 티트리 추출물을 가득 머금어 트러블 부위를 빠르게 진정시키고 각질을 케어하는 비건 인증 패드', 
    22000, 
    (SELECT id FROM public.categories WHERE name = 'pad'), 
    (SELECT id FROM public.skin_types WHERE name = '민감성 및 자극성'), 
    now() - interval '45 days', 
    now()
),
(
    '63d4efec-06f6-43d2-93b4-11b26b88c9e3', 
    (SELECT id FROM public.brands WHERE name = '메디힐'), 
    '티트리 트러블 패드', 
    '고농축 병풀 추출물(CICA)과 마데카소사이드 성분이 붉어지고 예민해진 피부를 빠르게 진정시키는 카밍 에센스', 
    24000, 
    (SELECT id FROM public.categories WHERE name = 'pad'), 
    (SELECT id FROM public.skin_types WHERE name = '지성 및 여드름성'), 
    now() - interval '42 days', 
    now()
),
(
    'cda7adcd-30e5-4610-8dd6-d1b48a3e018a', 
    (SELECT id FROM public.brands WHERE name = '넘버즈인'), 
    '5번 글루타치온 필름 패드', 
    '눈시림 없이 온 가족이 사용할 수 있는 백탁 없는 순한 데일리 물리적 자외선 차단제', 
    19800, 
    (SELECT id FROM public.categories WHERE name = 'pad'), 
    (SELECT id FROM public.skin_types WHERE name = '칙칙한 피부'), 
    now() - interval '23 days', 
    now()
)
ON CONFLICT (id) DO UPDATE SET
    brand_id = EXCLUDED.brand_id,
    product_name = EXCLUDED.product_name,
    description = EXCLUDED.description,
    price = EXCLUDED.price,
    category_id = EXCLUDED.category_id,
    skin_type_id = EXCLUDED.skin_type_id,
    updated_at = now();
