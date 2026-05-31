# TONES Backend API Specification

이 문서는 **TONES** 서비스의 백엔드(`TONES_Server`) API 명세서입니다. 
본 API는 FastAPI로 구현되어 있으며 기본 프리픽스는 `/api/v1` 입니다.

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

---

## 📊 API 요약 목록

| 태그 | 메서드 | 엔드포인트 | 인증 | 설명 |
| :--- | :--- | :--- | :---: | :--- |
| **Health** | `GET` | `/health` | ❌ | 서버 상태 확인 (Health Check) |
| **Auth** | `POST` | `/api/v1/auth/login/access-token` | ❌ | OAuth2 호환 로그인 및 액세스 토큰 발급 |
| | `POST` | `/api/v1/auth/signup` | ❌ | 신규 사용자 회원가입 |
| **Users** | `GET` | `/api/v1/users/me` | 🔑 | 로그인한 현재 사용자의 정보 조회 |
| **AI Search** | `POST` | `/api/v1/ai/search` | 🔑 | Pinecone 기반 시맨틱 검색 |
| | `POST` | `/api/v1/ai/generate` | 🔑 | 컨텍스트 기반 AI 답변 생성 |
| **Dashboard** | `GET` | `/api/v1/dashboard/products` | ❌ | 대시보드용 전체 제품 목록 조회 |
| | `GET` | `/api/v1/dashboard/reviews/latest` | ❌ | 최신 부정/일반 리뷰 목록 조회 |
| | `GET` | `/api/v1/dashboard/reviews/search` | ❌ | 키워드 기반 리뷰 필터링/검색 |
| | `GET` | `/api/v1/dashboard/reviews/product/{product_id}` | ❌ | 특정 제품 리뷰 상세 목록 조회 |
| | `POST` | `/api/v1/dashboard/reviews/bulk` | ❌ | 크롤링 리뷰 벌크 업로드 및 AI 파이프라인 처리 |
| | `GET` | `/api/v1/dashboard/statistics` | 🔑 | 대시보드 통계 차트 데이터 및 AI 브리핑 조회 |

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
  - `400 Bad Request`: 이메일 또는 비밀번호가 불일치하거나, 비활성화된 계정일 때
    ```json
    { "detail": "이메일 또는 비밀번호가 잘못되었습니다." }
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

#### `POST /api/v1/ai/search`
- **설명**: Pinecone 벡터 데이터베이스에 입력 쿼리를 전달하여 질문과 유사한 제품 리뷰 또는 데이터를 검색합니다.
- **인증**: JWT Bearer 토큰 필요 (🔑)
- **Request Body** (application/json):
  ```json
  {
    "query": "피부가 따갑고 민감해졌을 때 쓰기 좋은 순한 토너패드 추천해줘",
    "top_k": 5,
    "filter": {
      "brand_name": "아비브"
    }
  }
  ```
  - `query` (string, required): 검색할 자연어 질문/키워드
  - `top_k` (integer, optional, default: 5): 반환할 유사 아이템 개수
  - `filter` (object, optional): 메타데이터 필터 조건
- **Response** (200 OK):
  ```json
  {
    "query": "피부가 따갑고 민감해졌을 때 쓰기 좋은 순한 토너패드 추천해줘",
    "results": [
      {
        "id": "review-uuid-1",
        "score": 0.892,
        "metadata": {
          "product_name": "어성초 스팟패드 카밍터치",
          "review_text": "얼굴 뒤집어졌을 때 쓰면 진정에 엄청 좋아요. 순하고 트러블 안 남.",
          "sentiment": "positive",
          "rating": 5
        }
      }
    ]
  }
  ```

#### `POST /api/v1/ai/generate`
- **설명**: 프론트엔드에서 수집된 컨텍스트를 기반으로 LLM 답변을 만들어 제공합니다.
- **인증**: JWT Bearer 토큰 필요 (🔑)
- **Request Body** (application/json):
  ```json
  {
    "prompt": "검색 결과들을 요약해서 추천 이유를 작성해줘.",
    "context": "제품: 어성초 스팟패드 카밍터치\n사용자 후기: 민감성에 좋음, 진정 효과 빠름."
  }
  ```
  - `prompt` (string, required): AI에게 수행시킬 질문 또는 명령어
  - `context` (string, optional): 답변 생성에 주입할 참고 컨텍스트(텍스트 정보)
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
- **Request Body** (application/json):
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
- **인증**: JWT Bearer 토큰 필요 (🔑)
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
