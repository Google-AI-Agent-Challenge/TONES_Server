# TONES (Database) — Normalized Schema (3NF)

> **정규화 원칙**: 2NF / 3NF 기준 적용
> - 반복 문자열(브랜드, 카테고리, 피부 타입)은 별도 Lookup 테이블로 분리
> - 열거형 값(sentiment, source, reviewer_type, issue_type)은 PostgreSQL ENUM 타입으로 통일
> - `keywords TEXT[]` 배열은 다대다 중간 테이블로 정규화
> - `review_date` VARCHAR → DATE 타입으로 변경
> - pgvector 임베딩, 감성 점수 컬럼 및 `user_layouts` 테이블 반영

---

## ENUM Types

| ENUM Name       | Values                              | 사용 테이블   |
|-----------------|-------------------------------------|--------------|
| `sentiment_type` | `positive`, `neutral`, `negative`  | REVIEWS       |
| `source_type`    | `youtube`, `blog`, `naver_store`, `olive_young`, `mock`, `other` | REVIEWS |
| `reviewer_type`  | `general`, `influencer`, `expert`  | REVIEWS       |

| `issue_type`     | `ingredients`, `formulation`, `container`, `scent`, `irritation`, `none`, `other` | REVIEWS |

---

## BRANDS (Lookup Table)

| Column Name | Data Type    | Description      | Constraints                        |
|-------------|--------------|------------------|------------------------------------|
| id          | SERIAL       | Primary Key      | NOT NULL                           |
| name        | VARCHAR(255) | Brand Name       | Unique, NOT NULL                   |

---

## CATEGORIES (Lookup Table)

| Column Name | Data Type    | Description       | Constraints                       |
|-------------|--------------|-------------------|-----------------------------------|
| id          | SERIAL       | Primary Key       | NOT NULL                          |
| name        | VARCHAR(100) | Category Name     | Unique, NOT NULL                  |

---

## SKIN_TYPES (Lookup Table)

| Column Name | Data Type    | Description       | Constraints                       |
|-------------|--------------|-------------------|-----------------------------------|
| id          | SERIAL       | Primary Key       | NOT NULL                          |
| name        | VARCHAR(100) | Skin Type Name    | Unique, NOT NULL                  |

---

## USERS (Table)

| Column Name     | Data Type    | Description             | Constraints                              |
|-----------------|--------------|-------------------------|------------------------------------------|
| id              | UUID         | Primary Key             | UUID, auto-generated, NOT NULL           |
| email           | VARCHAR(255) | User Email              | Unique, NOT NULL                         |
| full_name       | VARCHAR(100) | User Full Name          | NOT NULL                                 |
| hashed_password | VARCHAR(255) | Hashed Password         | NOT NULL                                 |
| is_active       | BOOLEAN      | Account Status          | Default: TRUE                            |
| created_at      | TIMESTAMPTZ  | Creation Timestamp      | Default: Current Timestamp (UTC)         |
| updated_at      | TIMESTAMPTZ  | Update Timestamp        | Auto-updated via trigger                 |

---

## PRODUCTS (Table)

| Column Name    | Data Type    | Description                    | Constraints                                         |
|----------------|--------------|--------------------------------|-----------------------------------------------------|
| id             | UUID         | Primary Key                    | UUID, auto-generated, NOT NULL                      |
| brand_id       | INTEGER      | FK → BRANDS.id                 | NOT NULL, ON DELETE RESTRICT                        |
| product_name   | VARCHAR(255) | Product Name                   | NOT NULL                                            |
| description    | TEXT         | Product Description            | NULLABLE                                            |
| price          | NUMERIC      | Product Price                  | NULLABLE                                            |
| category_id    | INTEGER      | FK → CATEGORIES.id             | NOT NULL, ON DELETE RESTRICT                        |
| skin_type_id   | INTEGER      | FK → SKIN_TYPES.id             | NOT NULL, ON DELETE RESTRICT                        |
| created_at     | TIMESTAMPTZ  | Creation Timestamp             | Default: Current Timestamp (UTC)                    |
| updated_at     | TIMESTAMPTZ  | Update Timestamp               | Auto-updated via trigger                            |

---

## KEYWORDS (Table)

| Column Name | Data Type    | Description      | Constraints          |
|-------------|--------------|------------------|----------------------|
| id          | SERIAL       | Primary Key      | NOT NULL             |
| keyword     | VARCHAR(100) | Keyword Text     | Unique, NOT NULL     |

---

## REVIEWS (Table)

| Column Name       | Data Type      | Description                          | Constraints                                         |
|-------------------|----------------|--------------------------------------|-----------------------------------------------------|
| id                | UUID           | Primary Key                          | UUID, auto-generated, NOT NULL                      |
| product_id        | UUID           | FK → PRODUCTS.id                     | NOT NULL, ON DELETE CASCADE                         |
| source            | source_type    | Review Source                        | NOT NULL                                            |
| reviewer_type     | reviewer_type  | Reviewer Type                        | NOT NULL                                            |
| review_text       | TEXT           | Full Review Content                  | NOT NULL                                            |
| rating            | INTEGER        | Star Rating                          | CHECK (1–5), NOT NULL                               |
| review_date       | DATE           | Review Date                          | NOT NULL                                            |
| sentiment         | sentiment_type | Sentiment Classification             | NOT NULL                                            |
| sentiment_score   | NUMERIC        | Sentiment Probability Score          | NOT NULL                                            |
| issue_type        | issue_type     | Identified Issue Type                | NOT NULL                                            |
| ai_summary        | TEXT           | AI Generated Summary                 | NOT NULL                                            |
| embedding         | vector(768)    | pgvector 768-dim Embedding           | NULLABLE (HNSW index)                               |
| score_ingredients | NUMERIC        | Ingredient Sentiment Score           | Default: 0.5                                        |
| score_formulation | NUMERIC        | Formulation Sentiment Score          | Default: 0.5                                        |
| score_container   | NUMERIC        | Container Sentiment Score            | Default: 0.5                                        |
| review_id         | VARCHAR(255)   | Original Review ID from Source       | Unique within source, NOT NULL                      |
| created_at        | TIMESTAMPTZ    | Creation Timestamp                   | Default: Current Timestamp (UTC)                    |

---

## REVIEW_KEYWORDS (Junction Table — REVIEWS ↔ KEYWORDS)

| Column Name | Data Type | Description        | Constraints                          |
|-------------|-----------|--------------------|--------------------------------------|
| review_id   | UUID      | FK → REVIEWS.id    | NOT NULL, ON DELETE CASCADE          |
| keyword_id  | INTEGER   | FK → KEYWORDS.id   | NOT NULL, ON DELETE CASCADE          |

> **Primary Key**: (review_id, keyword_id) 복합 PK

---

## USER_LAYOUTS (Table)

| Column Name   | Data Type   | Description              | Constraints                          |
|---------------|-------------|--------------------------|--------------------------------------|
| user_token    | TEXT        | Primary Key (User Token) | NOT NULL                             |
| pinned_widget | TEXT        | Pinned Widget ID         | NULLABLE                             |
| updated_at    | TIMESTAMPTZ | Update Timestamp         | Auto-updated via trigger             |

---

## ERD (Entity Relationship)

```
BRANDS ──────────────┐
                     ↓
CATEGORIES ──────→ PRODUCTS ←── SKIN_TYPES
                     ↑
                   REVIEWS ──────────────── REVIEW_KEYWORDS ──── KEYWORDS
                   (ENUM: sentiment_type,
                          source_type,
                          reviewer_type,
                          issue_type)

USERS (독립)
USER_LAYOUTS (독립)
```

---

## 정규화 변경 요약

| 변경 항목 | Before | After |
|-----------|--------|-------|
| `products.brand_name` VARCHAR | 반복 문자열 | → `BRANDS` 테이블 FK |
| `products.category` VARCHAR | 반복 문자열 | → `CATEGORIES` 테이블 FK |
| `products.target_skin_type` VARCHAR | 반복 문자열 | → `SKIN_TYPES` 테이블 FK |
| `reviews.source` VARCHAR | 자유 문자열 | → `source_type` ENUM |
| `reviews.reviewer_type` VARCHAR | 자유 문자열 | → `reviewer_type` ENUM |
| `reviews.sentiment` VARCHAR | 자유 문자열 | → `sentiment_type` ENUM |
| `reviews.issue_type` VARCHAR | 자유 문자열 | → `issue_type` ENUM |
| `reviews.keywords` TEXT[] | 배열 컬럼 | → `KEYWORDS` + `REVIEW_KEYWORDS` |
| `reviews.review_date` VARCHAR | 문자열 날짜 | → `DATE` 타입 |
| `user_layouts` | 미문서화 | → 테이블 추가 |
| `reviews.embedding` | 미문서화 | → `vector(768)` 컬럼 추가 |
| `reviews.score_*` | 미문서화 | → 3개 NUMERIC 컬럼 추가 |
