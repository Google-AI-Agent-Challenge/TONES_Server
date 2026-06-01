-- 1. 기존 테이블 일괄 삭제 (의존성 제거 순서)
DROP TABLE IF EXISTS public.reviews CASCADE;
DROP TABLE IF EXISTS public.products CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;

-- 2. Users 테이블 생성 DDL
CREATE TABLE public.users (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Products 테이블 생성 DDL (ProductSchema 참고)
CREATE TABLE public.products (
    id VARCHAR(255) PRIMARY KEY,
    brand_name VARCHAR(255) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(255) NOT NULL,
    target_skin VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. Reviews 테이블 생성 DDL (ReviewSchema 참고)
CREATE TABLE public.reviews (
    id VARCHAR(255) PRIMARY KEY,
    product_id VARCHAR(255) NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    source VARCHAR(255) NOT NULL,
    reviewer_type VARCHAR(255),
    review_text TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review_date VARCHAR(100) NOT NULL,
    sentiment VARCHAR(50) NOT NULL,
    sentiment_score DOUBLE PRECISION,
    keywords TEXT[] NOT NULL DEFAULT '{}',
    issue_type VARCHAR(255),
    ai_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    review_id VARCHAR(255)
);
