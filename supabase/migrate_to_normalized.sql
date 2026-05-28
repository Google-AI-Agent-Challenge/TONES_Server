-- ========================================================== --
-- TONES Supabase 데이터 마이그레이션 스크립트 (Legacy -> Normalized) --
-- 설명: 기존 products, reviews, users 테이블의 데이터를             --
--       정규화 테이블(normalized_*)로 안전하게 복사 및 변환합니다.    --
-- ========================================================== --

BEGIN;

-- 혹시 기존에 생성된 정규화 테이블에 NOT NULL 제약조건이 있을 경우를 대비해 제약조건 해제
ALTER TABLE public.normalized_reviews ALTER COLUMN sentiment_score DROP NOT NULL;

-- ========================================================== --
-- Phase 1: 마스터 테이블(Master Tables) 데이터 구축             --
-- ========================================================== --

DO $$ BEGIN RAISE NOTICE '1단계: 마스터 테이블 마이그레이션 시작...'; END $$;

-- 1. 브랜드 마스터 데이터 삽입
INSERT INTO public.normalized_brands (name)
SELECT DISTINCT COALESCE(NULLIF(trim(brand_name), ''), '기타') 
FROM public.products
ON CONFLICT (name) DO NOTHING;

-- 2. 상품 카테고리 마스터 데이터 삽입
INSERT INTO public.normalized_categories (name)
SELECT DISTINCT COALESCE(NULLIF(trim(category), ''), '일반') 
FROM public.products
ON CONFLICT (name) DO NOTHING;

-- 3. 피부 타입 마스터 데이터 삽입 (기본 데이터 + 제품 target_skin + 리뷰 reviewer_type)
INSERT INTO public.normalized_skin_types (name) VALUES 
('민감성'), ('건성'), ('지성'), ('복합성'), ('수부지'), ('여드름성'), ('일반')
ON CONFLICT (name) DO NOTHING;

INSERT INTO public.normalized_skin_types (name)
SELECT DISTINCT trim(val)
FROM public.products,
regexp_split_to_table(products.target_skin, '[,&/및]') AS val
WHERE val IS NOT NULL AND trim(val) <> ''
ON CONFLICT (name) DO NOTHING;

INSERT INTO public.normalized_skin_types (name)
SELECT DISTINCT trim(reviewer_type)
FROM public.reviews
WHERE reviewer_type IS NOT NULL AND trim(reviewer_type) <> ''
ON CONFLICT (name) DO NOTHING;

-- 4. 리뷰 출처 마스터 데이터 삽입
INSERT INTO public.normalized_review_sources (name)
SELECT DISTINCT COALESCE(NULLIF(trim(source), ''), '기타') 
FROM public.reviews
ON CONFLICT (name) DO NOTHING;

-- 5. ABSA 감성 분석 관점 마스터 데이터 삽입
INSERT INTO public.normalized_aspects (name, display_name) VALUES
('ingredients', '성분/고민'),
('formulation', '제형/발림'),
('container', '용기/디자인')
ON CONFLICT (name) DO NOTHING;

-- 6. 리뷰 키워드 마스터 데이터 삽입
INSERT INTO public.normalized_keywords (word)
SELECT DISTINCT trim(w.val)
FROM public.reviews r
CROSS JOIN LATERAL unnest(r.keywords) AS w(val)
WHERE w.val IS NOT NULL AND trim(w.val) <> ''
ON CONFLICT (word) DO NOTHING;

-- 7. 리뷰 이슈 타입 마스터 데이터 삽입
INSERT INTO public.normalized_issue_types (name)
SELECT DISTINCT trim(val)
FROM public.reviews,
regexp_split_to_table(reviews.issue_type, '[,&/및]') AS val
WHERE val IS NOT NULL AND trim(val) <> ''
ON CONFLICT (name) DO NOTHING;


-- ========================================================== --
-- Phase 2: 주요 엔티티 테이블(Main Entity Tables) 데이터 이행   --
-- ========================================================== --

DO $$ BEGIN RAISE NOTICE '2단계: 주요 엔티티 테이블 마이그레이션 시작...'; END $$;

-- 8. 정규화된 상품 데이터 이행 (브랜드, 카테고리 FK 매핑)
INSERT INTO public.normalized_products (id, brand_id, category_id, name, description, price, created_at, updated_at)
SELECT 
    p.id,
    b.id AS brand_id,
    c.id AS category_id,
    p.product_name AS name,
    NULL AS description,
    0 AS price,
    p.created_at,
    p.created_at AS updated_at
FROM public.products p
LEFT JOIN public.normalized_brands b ON b.name = COALESCE(NULLIF(trim(p.brand_name), ''), '기타')
LEFT JOIN public.normalized_categories c ON c.name = COALESCE(NULLIF(trim(p.category), ''), '일반')
ON CONFLICT (id) DO NOTHING;

-- 9. 상품-피부 타입 다대다(N:M) 관계 이행 (regexp_split_to_table 분해)
INSERT INTO public.normalized_product_skin_types (product_id, skin_type_id)
SELECT DISTINCT
    p.id AS product_id,
    s.id AS skin_type_id
FROM public.products p
CROSS JOIN LATERAL regexp_split_to_table(p.target_skin, '[,&/및]') AS val
JOIN public.normalized_skin_types s ON s.name = trim(val)
WHERE val IS NOT NULL AND trim(val) <> ''
ON CONFLICT (product_id, skin_type_id) DO NOTHING;

-- 10. 정규화된 리뷰 데이터 이행 (출처, 작성자 피부 타입 FK 매핑)
INSERT INTO public.normalized_reviews (id, product_id, source_id, reviewer_skin_type_id, review_text, rating, review_date, sentiment, sentiment_score, ai_summary, review_id, created_at)
SELECT 
    r.id,
    r.product_id,
    src.id AS source_id,
    s.id AS reviewer_skin_type_id,
    r.review_text,
    r.rating,
    COALESCE(r.review_date, CURRENT_DATE) AS review_date,
    r.sentiment,
    r.sentiment_score,
    r.ai_summary,
    r.review_id,
    r.created_at
FROM public.reviews r
LEFT JOIN public.normalized_review_sources src ON src.name = COALESCE(NULLIF(trim(r.source), ''), '기타')
LEFT JOIN public.normalized_skin_types s ON s.name = trim(r.reviewer_type)
ON CONFLICT (id) DO NOTHING;


-- ========================================================== --
-- Phase 3: 관계 및 감성 점수 테이블(Junction & Score Tables) 이행 --
-- ========================================================== --

DO $$ BEGIN RAISE NOTICE '3단계: 교차 및 감성 분석 상세 점수 테이블 마이그레이션 시작...'; END $$;

-- 11. 리뷰-키워드 다대다(N:M) 관계 이행
INSERT INTO public.normalized_review_keywords (review_id, keyword_id)
SELECT DISTINCT
    r.id AS review_id,
    k.id AS keyword_id
FROM public.reviews r
CROSS JOIN LATERAL unnest(r.keywords) AS w(val)
JOIN public.normalized_keywords k ON k.word = trim(w.val)
WHERE w.val IS NOT NULL AND trim(w.val) <> ''
ON CONFLICT (review_id, keyword_id) DO NOTHING;

-- 12. 리뷰-이슈 타입 다대다(N:M) 관계 이행
INSERT INTO public.normalized_review_issue_types (review_id, issue_type_id)
SELECT DISTINCT
    r.id AS review_id,
    i.id AS issue_type_id
FROM public.reviews r
CROSS JOIN LATERAL regexp_split_to_table(r.issue_type, '[,&/및]') AS val
JOIN public.normalized_issue_types i ON i.name = trim(val)
WHERE val IS NOT NULL AND trim(val) <> ''
ON CONFLICT (review_id, issue_type_id) DO NOTHING;

-- 13. ABSA 세부 감성 점수 데이터 이행
-- 설명: 기존 reviews 테이블에 score_* 컬럼이 존재할 경우 이를 읽어 들이고, 
--       만약 없을 경우(Self-Healing 적용 테이블의 경우) ai_summary 텍스트에서 점수를 파싱하여 적재합니다.
DO $$
DECLARE
    column_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'reviews' 
          AND column_name = 'score_ingredients'
    ) INTO column_exists;

    IF column_exists THEN
        -- score_* 세부 스코어 컬럼이 존재할 경우 직접 데이터 조인 인서트
        INSERT INTO public.normalized_review_aspect_scores (review_id, aspect_id, score)
        SELECT 
            r.id AS review_id,
            a.id AS aspect_id,
            CASE 
                WHEN a.name = 'ingredients' THEN COALESCE(r.score_ingredients::NUMERIC, 0.5)
                WHEN a.name = 'formulation' THEN COALESCE(r.score_formulation::NUMERIC, 0.5)
                WHEN a.name = 'container' THEN COALESCE(r.score_container::NUMERIC, 0.5)
            END AS score
        FROM public.reviews r
        CROSS JOIN public.normalized_aspects a
        ON CONFLICT (review_id, aspect_id) DO NOTHING;
    ELSE
        -- 자가 치유(Self-Healing) 모델로 인해 컬럼이 존재하지 않는 경우 ai_summary 텍스트로부터 정규표현식 파싱 적재
        INSERT INTO public.normalized_review_aspect_scores (review_id, aspect_id, score)
        SELECT 
            r.id AS review_id,
            a.id AS aspect_id,
            CASE 
                WHEN a.name = 'ingredients' THEN 
                    COALESCE(NULLIF(substring(r.ai_summary from '\[성분/고민\]:\s*([0-9.]+)'), '')::NUMERIC, 0.5)
                WHEN a.name = 'formulation' THEN 
                    COALESCE(NULLIF(substring(r.ai_summary from '\[제형/발림\]:\s*([0-9.]+)'), '')::NUMERIC, 0.5)
                WHEN a.name = 'container' THEN 
                    COALESCE(NULLIF(substring(r.ai_summary from '\[용기/디자인\]:\s*([0-9.]+)'), '')::NUMERIC, 0.5)
            END AS score
        FROM public.reviews r
        CROSS JOIN public.normalized_aspects a
        ON CONFLICT (review_id, aspect_id) DO NOTHING;
    END IF;
END $$;


-- ========================================================== --
-- Phase 4: 사용자 및 관리자 데이터 이행                           --
-- ========================================================== --

DO $$ BEGIN RAISE NOTICE '4단계: 사용자 테이블 마이그레이션 시작...'; END $$;

-- 14. 사용자 테이블 데이터 이행 (중복 방지 이메일 기준 적용)
DO $$
DECLARE
    table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
          AND table_name = 'users'
    ) INTO table_exists;

    IF table_exists THEN
        EXECUTE '
            INSERT INTO public.normalized_users (id, email, full_name, hashed_password, is_active, created_at, updated_at)
            SELECT 
                id,
                email,
                full_name,
                hashed_password,
                is_active,
                COALESCE(created_at, timezone(''utc''::text, now())),
                COALESCE(updated_at, timezone(''utc''::text, now()))
            FROM public.users
            ON CONFLICT (email) DO NOTHING;
        ';
        RAISE NOTICE 'public.users 데이터 이행 완료.';
    ELSE
        RAISE NOTICE 'public.users 테이블이 존재하지 않아 사용자 데이터 마이그레이션을 건너뜁니다.';
    END IF;
END $$;

COMMIT;

DO $$ BEGIN RAISE NOTICE '🎉 성공적으로 모든 데이터 마이그레이션이 완료되었습니다!'; END $$;
