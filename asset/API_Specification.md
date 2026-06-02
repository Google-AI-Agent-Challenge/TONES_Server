# TONES Backend API Specification

이 문서는 **TONES** 서비스의 백엔드(`TONES_Server`) API 명세서입니다. 
본 API는 FastAPI로 구현되어 있으며 기본 프리픽스는 `/api/v1` 입니다.

> **마지막 업데이트**: 2026-06-02 (실제 구현 코드 기반 동기화)

---

## 📌 공통 사양

### Base URL
- Local 개발 환경: `http://localhost:8080` (기본 포트)
- API 기본 경로: `/api/v1` (단, `/health`는 루트 경로)

### 인증 방식 (Authentication)
- **JWT (Json Web Token) Bearer 인증**을 사용합니다.
- 인증이 필요한 API는 요청 헤더에 다음 형식을 포함해야 합니다:
  ```http
  Authorization: Bearer <Your_JWT_Access_Token>
  ```

> ⚠️ **[프로토타입 개발 주의]** 현재 `app/api/deps.py`의 `get_current_user()`가 JWT 검증을 비활성화하고 테스트용 더미 사용자(`test@example.com`)를 항상 반환하도록 설정되어 있다. 🔑 표시 API도 실질적으로 토큰 없이 호출 가능하며, 프로덕션 배포 전 반드시 복원이 필요하다.

---

## 📊 API 요약 목록

| 태그 | 메서드 | 엔드포인트 | 인증 | 설명 |
| :--- | :--- | :--- | :---: | :--- |
| **Health** | `GET` | `/health` | ❌ | 서버 상태 확인 (Health Check) |
| **Auth** | `POST` | `/api/v1/auth/login/access-token` | ❌ | OAuth2 호환 로그인 및 액세스 토큰 발급 |
| | `POST` | `/api/v1/auth/signup` | ❌ | 신규 사용자 회원가입 |
| | `POST` | `/api/v1/auth/find-email` | ❌ | 이름 기반 가입 이메일 찾기 |
| | `POST` | `/api/v1/auth/find-password` | ❌ | 이메일 및 이름 기반 임시 비밀번호 재발급 |
| **Users** | `GET` | `/api/v1/users/me` | 🔑 | 로그인한 현재 사용자의 정보 조회 |
| **AI Search** | `POST` | `/api/v1/ai/search` | 🔑 | Cloud SQL pgvector 기반 시맨틱 검색 |
| | `POST` | `/api/v1/ai/generate` | 🔑 | Vertex AI(Gemini) 기반 AI 답변 생성 |
| **Dashboard** | `GET` | `/api/v1/dashboard/products` | ❌ | 대시보드용 전체 제품 목록 조회 |
| | `GET` | `/api/v1/dashboard/reviews/latest` | ❌ | 최신 부정/일반 리뷰 목록 조회 |
| | `GET` | `/api/v1/dashboard/reviews/search` | ❌ | 키워드 기반 리뷰 필터링/검색 |
| | `GET` | `/api/v1/dashboard/reviews/product/{product_id}` | ❌ | 특정 제품 리뷰 상세 목록 조회 |
| | `POST` | `/api/v1/dashboard/reviews/bulk` | ❌ | 크롤링 리뷰 벌크 업로드 및 AI 파이프라인 처리 |
| | `GET` | `/api/v1/dashboard/statistics` | 🔑* | 대시보드 통계 차트 데이터 및 AI 브리핑 조회 |
| | `GET` | `/api/v1/dashboard/layout` | ❌ | 사용자 대시보드 위젯 고정 레이아웃 조회 |
| | `POST` | `/api/v1/dashboard/layout` | ❌ | 사용자 대시보드 위젯 고정 레이아웃 저장/업데이트 |
| | `POST` | `/api/v1/dashboard/reviews/ids` | ❌ | ID 배열 기반 매칭 리뷰 상세 목록 조회 |
| **Compat** | `GET` | `/api/products` | ❌ | 프론트엔드 호환용 전체 제품 목록 조회 |
| | `GET` | `/api/reviews` | ❌ | 프론트엔드 호환용 리뷰 조회 (분기 처리) |
| | `GET` | `/api/reviews/batch` | ❌ | 프론트엔드 호환용 ID 기반 리뷰 조회 |

---

## 🔒 상세 API 명세

### 1. Health Check (서버 헬스 체크)

#### `GET /health`
- **설명**: 서버의 구동 상태를 확인합니다.
- **인증**: 필요 없음 (❌)
- **Response** (200 OK):
  ```json
  {
    "status": "healthy",
    "project": "TONES",
    "version": "1.0.0"
  }
  ```

---

### 2. Auth (인증 및 계정 관리)

#### `POST /api/v1/auth/login/access-token`
- **설명**: OAuth2 규격에 따라 사용자의 이메일과 비밀번호를 검증하고 JWT 액세스 토큰을 반급합니다.
- **인증**: 필요 없음 (❌)
- **Request Body** (Form-Data):
  - `username` (string, required): 가입된 사용자 이메일 (예: `user@example.com`)
  - `password` (string, required): 사용자 비밀번호
- **Response** (200 OK):
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: 이메일 또는 비밀번호가 불일치할 때
    ```json
    { "detail": "이메일 또는 비밀번호가 잘못되었습니다." }
    ```
  - `400 Bad Request`: 비활성화된 계정일 때
    ```json
    { "detail": "비활성화된 사용자 계정입니다." }
    ```

#### `POST /api/v1/auth/signup`
- **설명**: 신규 사용자로 가입합니다.
- **인증**: 필요 없음 (❌)
- **Request Body** (application/json):
  ```json
  {
    "email": "user@example.com",
    "password": "strongpassword123",
    "full_name": "홍길동"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "id": "uuid-string-here",
    "email": "user@example.com",
    "full_name": "홍길동",
    "is_active": true
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: 이미 등록된 이메일 주소일 때
    ```json
    { "detail": "이미 존재하는 이메일입니다." }
    ```

#### `POST /api/v1/auth/find-email`
- **설명**: 제공된 전체 이름(`full_name`)을 기준으로 가입된 이메일을 검색하여 반환합니다.
- **인증**: 필요 없음 (❌)
- **Request Body** (application/json):
  ```json
  {
    "full_name": "홍길동"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Error Responses**:
  - `404 Not Found`: 해당 이름으로 가입된 사용자가 존재하지 않을 때
    ```json
    { "detail": "해당 이름으로 등록된 사용자를 찾을 수 없습니다." }
    ```

#### `POST /api/v1/auth/find-password`
- **설명**: 가입된 이메일과 이름(`full_name`)을 기반으로 임시 비밀번호를 무작위 생성하여 업데이트한 뒤 발급합니다.
- **인증**: 필요 없음 (❌)
- **Request Body** (application/json):
  ```json
  {
    "email": "user@example.com",
    "full_name": "홍길동"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "temp_password": "aBcD12eF"
  }
  ```
- **Error Responses**:
  - `404 Not Found`: 이메일과 이름이 일치하는 사용자를 찾을 수 없을 때
    ```json
    { "detail": "이메일과 이름이 일치하는 사용자를 찾을 수 없습니다." }
    ```

---

### 3. Users (사용자 정보)

#### `GET /api/v1/users/me`
- **설명**: 현재 로그인한(인증 헤더를 보낸) 사용자의 정보를 상세 조회합니다.
- **인증**: JWT Bearer 토큰 필요 (🔑)
- **Response** (200 OK):
  ```json
  {
    "id": "uuid-string-here",
    "email": "user@example.com",
    "full_name": "홍길동",
    "is_active": true
  }
  ```
- **Error Responses**:
  - `401 Unauthorized`: 유효하지 않거나 만료된 토큰일 경우

---

### 4. AI Search (AI 분석 및 검색)

> **벡터 검색 스택**: Pinecone에서 **GCP Cloud SQL PostgreSQL + pgvector** 로 전환됨.  
> 임베딩은 **Vertex AI `text-embedding-004`** (폴백: Gemini HTTP API)를 사용하고,  
> 텍스트 생성은 **Vertex AI `gemini-2.0-flash`** (폴백: `gemini-1.5-flash` → HTTP API)를 사용한다.

#### `POST /api/v1/ai/search`
- **설명**: 입력 쿼리를 Vertex AI 임베딩으로 변환한 뒤, Cloud SQL PostgreSQL의 pgvector 확장(`<=>` 코사인 거리 연산자)을 이용해 `reviews` 테이블에서 의미적으로 유사한 리뷰를 검색합니다.
- **인증**: JWT Bearer 토큰 필요 (🔑)
- **Request Body** (application/json):
  ```json
  {
    "query": "피부가 따갑고 민감해졌을 때 쓰기 좋은 순한 토너패드 추천해줘",
    "top_k": 5,
    "filter": {
      "product_id": "prod-uuid-1"
    }
  }
  ```
  - `query` (string, required): 검색할 자연어 질문/키워드
  - `top_k` (integer, optional, default: 5): 반환할 유사 리뷰 개수
  - `filter` (object, optional): 필터 조건. 현재 `product_id` 키만 지원
- **Response** (200 OK):
  ```json
  {
    "query": "피부가 따갑고 민감해졌을 때 쓰기 좋은 순한 토너패드 추천해줘",
    "results": [
      {
        "id": "review-uuid-1",
        "score": 0.892,
        "metadata": {
          "review_text": "얼굴 뒤집어졌을 때 쓰면 진정에 엄청 좋아요. 순하고 트러블 안 남.",
          "rating": 5,
          "review_date": "2026-05-30",
          "sentiment": "positive",
          "issue_type": "없음",
          "ai_summary": "트러블 진정 효과가 우수하고 순한 성분으로 민감 피부에 적합함"
        }
      }
    ]
  }
  ```
  - `score`: pgvector 코사인 유사도 (`1 - 코사인거리`, 1.0에 가까울수록 유사)
  - `metadata` 필드는 `reviews` 테이블의 실제 컬럼 기반 (`review_text`, `rating`, `review_date`, `sentiment`, `issue_type`, `ai_summary`)

#### `POST /api/v1/ai/generate`
- **설명**: 제공된 컨텍스트를 프롬프트에 주입하여 Vertex AI Gemini 모델로 한국어 답변을 생성합니다.
- **인증**: JWT Bearer 토큰 필요 (🔑)
- **Request Body** (application/json):
  ```json
  {
    "prompt": "검색 결과들을 요약해서 추천 이유를 작성해줘.",
    "context": "제품: 어성초 스팟패드 카밍터치\n사용자 후기: 민감성에 좋음, 진정 효과 빠름."
  }
  ```
  - `prompt` (string, required): AI에게 수행시킬 질문 또는 명령어
  - `context` (string, optional): 답변 생성에 주입할 참고 컨텍스트
- **Response** (200 OK):
  ```json
  {
    "answer": "검색 결과에 근거했을 때, '어성초 스팟패드 카밍터치'는 어성초 성분이 함유되어 민감해진 피부를 빠르게 진정시킨다는 긍정 피드백이 많아 적극 추천합니다."
  }
  ```

---

### 5. Dashboard (대시보드 관리)

#### `GET /api/v1/dashboard/products`
- **설명**: 대시보드 제품 라인업 필터 및 상세 목록에 매핑할 전체 등록 화장품 제품들을 조회합니다.
- **인증**: 필요 없음 (❌)
- **Response** (200 OK):
  ```json
  [
    {
      "id": "prod-uuid-1",
      "brand_name": "아비브",
      "product_name": "어성초 스팟패드 카밍터치",
      "category": "토너패드",
      "target_skin": "민감성",
      "created_at": "2026-05-31T06:00:00Z"
    }
  ]
  ```

#### `GET /api/v1/dashboard/reviews/latest`
- **설명**: 대시보드의 메인 화면에 표시할 부정 또는 일반 등 최근 수집된 실시간 리뷰 피드를 최신 등록 순으로 정렬해 제공합니다.
- **인증**: 필요 없음 (❌)
- **Query Parameters**:
  - `limit` (integer, optional, default: 20): 조회할 최근 리뷰의 개수 한도
- **Response** (200 OK):
  ```json
  [
    {
      "id": "rev-uuid-1",
      "product_id": "prod-uuid-1",
      "source": "올리브영",
      "reviewer_type": "수분부족지성",
      "review_text": "제품이 너무 두껍고 에센스가 부족해서 아쉬워요.",
      "rating": 2,
      "review_date": "2026-05-30",
      "sentiment": "negative",
      "sentiment_score": 0.21,
      "keywords": ["에센스부족", "두꺼움"],
      "issue_type": "사용감",
      "ai_summary": "에센스 양이 적고 패드가 두꺼워 사용 시 아쉽다는 피드백이 있음",
      "created_at": "2026-05-31T06:30:00Z",
      "review_id": "olv-987654",
      "products": {
        "id": "prod-uuid-1",
        "brand_name": "아비브",
        "product_name": "어성초 스팟패드 카밍터치",
        "category": "토너패드",
        "target_skin": "민감성"
      }
    }
  ]
  ```

#### `GET /api/v1/dashboard/reviews/search`
- **설명**: 쉼표(,) 등으로 나열된 다중 키워드를 기준으로 필터링된 고객 리뷰 정보를 검색 및 반환합니다.
- **인증**: 필요 없음 (❌)
- **Query Parameters**:
  - `keywords` (array of strings, optional): 검색용 키워드 배열. 쉼표(`,`)를 활용하여 문자열 하나로 전달할 수도 있음 (예: `keywords=트러블,자극` 또는 여러 개의 파라미터 `keywords=트러블&keywords=자극`)
  - `limit` (integer, optional, default: 20): 반환할 매칭 리뷰 수
- **Response** (200 OK):
  - [GET `/reviews/latest`](#get-apiv1dashboardreviewslatest)와 동일한 형식의 `ReviewSchema` 배열 반환.

#### `GET /api/v1/dashboard/reviews/product/{product_id}`
- **설명**: 특정 제품에만 속한 사용자 리뷰 목록을 페이지네이션 및 제한된 수로 상세 조회합니다.
- **인증**: 필요 없음 (❌)
- **Path Parameters**:
  - `product_id` (string, required): 조회할 대상 상품 ID
- **Query Parameters**:
  - `limit` (integer, optional, default: 20): 최대로 가져올 리뷰 개수
- **Response** (200 OK):
  - [GET `/reviews/latest`](#get-apiv1dashboardreviewslatest)와 동일한 형식의 `ReviewSchema` 배열 반환.

#### `POST /api/v1/dashboard/reviews/bulk`
- **설명**: 크롤러 및 배치 스크립트를 통해 수집된 다수의 원본 리뷰 데이터를 대량으로 업로드합니다. 백엔드의 AI 분석 파이프라인(감성 분석, 키워드 추출, 이슈 타입 결정 등)을 트리거하여 정제 과정을 거친 뒤 DB에 최종 반영합니다.
- **인증**: 현재 별도 인증 미적용 (❌)
- **Request Body** (application/json) — `ReviewCreate` 스키마 배열:
  ```json
  [
    {
      "product_id": "prod-uuid-1",
      "content": "트러블 진정에 직빵입니다. 붉은 기가 많이 가라앉았어요.",
      "rating": 5,
      "skin_type": "민감성 건성",
      "reviewer_type": "20대 여성",
      "source": "올리브영",
      "review_date": "2026-05-31",
      "review_id": "olv-123456"
    }
  ]
  ```
  - `product_id` (string, **required**): 대상 제품 UUID
  - `content` (string, **required**): 리뷰 원문 텍스트
  - `rating` (integer, **required**): 평점 (1~5)
  - `skin_type` (string, optional): 피부 타입
  - `reviewer_type` (string, optional): 리뷰어 유형
  - `source` (string, optional, default: `"올리브영"`): 리뷰 출처
  - `review_date` (string, optional): 리뷰 작성일 (YYYY-MM-DD)
  - `review_id` (string, optional): 출처 플랫폼 고유 ID (중복 방지용)
- **Response** (201 Created):
  ```json
  {
    "status": "success",
    "processed_count": 1,
    "inserted_count": 1,
    "errors": []
  }
  ```

#### `GET /api/v1/dashboard/statistics`
- **설명**: 대시보드 시각화 차트(Recharts 연동 등)용 전체 집계 데이터와 LLM이 작성한 기간별 종합 AI 트렌드 리포트를 한 번에 받아오는 코어 API입니다.
- **인증**: JWT Bearer 토큰 명시 (🔑*) — 단, 현재 프로토타입 환경에서는 토큰 없이도 호출 가능 (공통 주의사항 참고)
- **Query Parameters**:
  - `product_id` (string, optional): 지정할 시 특정 제품에 국한된 통계를 제공하며, 비워둘 시 전체 취급 제품의 총합 합산 결과를 리턴합니다.
  - `period` (integer, optional, default: 7): 통계 분석을 집계할 조회 기간 범위 (일(day) 수 단위)
- **Response** (200 OK):
  ```json
  {
    "product_id": "prod-uuid-1",
    "period_days": 7,
    "summary": {
      "total_reviews": 1420,
      "positive_count": 1150,
      "negative_count": 270,
      "average_rating": 4.2
    },
    "trend_chart_data": [
      {
        "date": "2026-05-25",
        "positive": 150,
        "negative": 32,
        "average_rating": 4.1
      },
      {
        "date": "2026-05-26",
        "positive": 180,
        "negative": 28,
        "average_rating": 4.3
      }
    ],
    "issue_distribution": {
      "사용감": 120,
      "트러블/자극": 85,
      "에센스양": 45,
      "패드두께": 20
    },
    "ai_trend_briefing": "최근 7일간 '어성초 스팟패드 카밍터치'에 관한 긍정 리뷰 비율은 약 81%로 유지되고 있습니다. 주로 '빠른 트러블 진정 효과'에 극찬이 있으나, 일부 사용감 측면에서 '패드 에센스가 금방 마른다'는 의견이 20%가량 증가했으므로 패키징 및 액량 보강을 검토해볼 필요가 있습니다."
  }
  ```

#### `GET /api/v1/dashboard/layout`
- **설명**: 사용자 대시보드 위젯의 고정 레이아웃을 조회합니다.
- **인증**: 필요 없음 (❌)
- **Query Parameters**:
  - `token` (string, required): 사용자 식별 토큰
- **Response** (200 OK):
  ```json
  {
    "pinned_widget": "widget-1,widget-2"
  }
  ```

#### `POST /api/v1/dashboard/layout`
- **설명**: 사용자 대시보드 위젯의 고정 레이아웃을 저장하거나 업데이트합니다.
- **인증**: 필요 없음 (❌)
- **Request Body** (application/json):
  ```json
  {
    "token": "user-token-123",
    "pinned_widget": "widget-1,widget-2"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "success": true
  }
  ```

#### `POST /api/v1/dashboard/reviews/ids`
- **설명**: 제공된 ID 배열과 일치하는 리뷰 상세 목록을 조회합니다.
- **인증**: 필요 없음 (❌)
- **Request Body** (application/json):
  ```json
  {
    "ids": ["rev-uuid-1", "rev-uuid-2"]
  }
  ```
- **Response** (200 OK):
  - [GET `/reviews/latest`](#get-apiv1dashboardreviewslatest)와 동일한 형식의 `ReviewSchema` 배열 반환.

---

### 6. Frontend Compatibility (프론트엔드 호환용 API)

프론트엔드 레거시 코드 또는 특정 호환성 유지를 위해 제공되는 API 제품군입니다. 프리픽스로 `/api`를 사용합니다.

#### `GET /api/products`
- **설명**: 프론트엔드 호환용 전체 제품 목록을 조회합니다.
- **인증**: 필요 없음 (❌)
- **Response** (200 OK):
  - [GET `/api/v1/dashboard/products`](#get-apiv1dashboardproducts)와 동일한 형식의 `ProductSchema` 배열 반환.

#### `GET /api/reviews`
- **설명**: 조건(특정 상품, 특정 키워드, 혹은 최신 리뷰)에 맞춰 분기 처리하여 리뷰 목록을 조회합니다.
- **인증**: 필요 없음 (❌)
- **Query Parameters**:
  - `limit` (integer, optional, default: 20): 조회할 리뷰 수
  - `product_id` (string, optional): 특정 상품 필터 ID. 지정 시 해당 상품 리뷰를 조회함.
  - `keywords` (string, optional): 쉼표로 구분된 검색 키워드. 지정 시 키워드 매칭 리뷰를 조회함.
- **Response** (200 OK):
  - [GET `/reviews/latest`](#get-apiv1dashboardreviewslatest)와 동일한 형식의 `ReviewSchema` 배열 반환.

#### `GET /api/reviews/batch`
- **설명**: 쉼표로 구분된 ID 문자열을 기반으로 리뷰 상세 목록을 조회합니다.
- **인증**: 필요 없음 (❌)
- **Query Parameters**:
  - `ids` (string, required): 쉼표로 구분된 ID 목록 (예: `rev-1,rev-2,rev-3`)
- **Response** (200 OK):
  - [GET `/reviews/latest`](#get-apiv1dashboardreviewslatest)와 동일한 형식의 `ReviewSchema` 배열 반환.
