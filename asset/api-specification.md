# TONES Backend API Specification

이 문서는 **TONES** B2B AI 리뷰 분석 대시보드 백엔드 서비스(`TONES_Server`)의 공식 API 명세서입니다. 
본 백엔드 시스템은 FastAPI 비동기 프레임워크와 GCP Cloud SQL pgvector 확장 및 Vertex AI(Gemini 2.0) 생태계를 기반으로 구축되었습니다.

> **마지막 업데이트**: 2026-06-02 (`GET /api/reviews/count` 신규 추가 — 프론트엔드 병렬 청크 로딩 지원)

---

## 📌 공통 사양

### Base URL
- **로컬 개발 환경**: `http://localhost:8080` (기본 포트)
- **API 기본 경로 (Prefix)**: `/api` (단, `/health`는 예외적으로 루트 경로 사용)

### 인증 방식 (Authentication)
- **JWT (Json Web Token) Bearer 인증**을 사용합니다.
- 인증이 필요한 API는 HTTP 요청 헤더에 다음 규격을 필수로 포함해야 합니다:
  ```http
  Authorization: Bearer <Your_JWT_Access_Token>
  ```
- **권한 관리 (RBAC)**: 사용자 계정은 `role` 속성(`super_admin`, `analyst`, `manager` 등)을 가집니다. 특정 관리자 제어 API의 경우 `super_admin` 권한이 검증되어야 통과됩니다.
- *가용성 백업*: 개발 편의성 및 로컬 가상 검증을 위해, 토큰 누락/손상 시 `test@example.com` (슈퍼 관리자 권한)으로의 Graceful Fallback Mock 인증을 지원합니다.

---

## 📊 API 요약 목록

### 1. 헬스체크 및 계정/인증 (Health & Auth)
| 태그 | 메서드 | 엔드포인트 | 인증 | 설명 |
| :--- | :--- | :--- | :---: | :--- |
| **Health** | `GET` | `/health` | ❌ | 백엔드 서버 상태 확인 (Health Check) |
| **Auth** | `POST` | `/api/auth/login` | ❌ | JSON 기반 일반 사용자 로그인 및 JWT 발급 |
| | `POST` | `/api/auth/login/access-token` | ❌ | OAuth2 표준 Form 기반 로그인 및 토큰 발급 |
| | `POST` | `/api/auth/logout` | ❌ | 사용자 세션 파기 및 로그아웃 |
| | `POST` | `/api/auth/signup` | ❌ | B2B 플랫폼 신규 사용자 회원가입 |
| | `POST` | `/api/auth/find-email` | ❌ | 이름 기반 가입 이메일(아이디) 찾기 |
| | `POST` | `/api/auth/find-password` | ❌ | 이메일 및 이름 기반 임시 비밀번호 재설정 |
| **Users** | `GET` | `/api/users/me` | 🔑 | 현재 로그인한 사용자의 권한 및 상태 상세 프로필 조회 |

### 2. 홈 대시보드 (homePage)
| 태그 | 메서드 | 엔드포인트 | 인증 | 설명 |
| :--- | :--- | :--- | :---: | :--- |
| **Dashboard** | `GET` | `/api/dashboard/summary` | 🔑 | 만족도 평균, 전체 리뷰 수, 우선 확인 요약 (WoW 전주 대비 포함) |
| | `GET` | `/api/dashboard/trending-keywords` | 🔑 | 기간 내 언급 빈도 최다 Top 5 키워드 목록 조회 |
| | `GET` | `/api/dashboard/negative-trend` | 🔑 | Recharts 차트 연동용 부정 리뷰 일자별 시계열 발생 추이 |
| | `GET` | `/api/dashboard/insights` | 🔑 | 3대 화장품 품질 만족도(성분/제형/용기) WoW 변동율 |
| | `GET` | `/api/dashboard/ai-briefing` | 🔑 | Gemini 2.0-flash 기반의 대시보드 실시간 AI 트렌드 보고 브리핑 |
| | `POST` | `/api/dashboard/report` | 🔑 | AI 분석 요약 보고서(Markdown) 및 엑셀 로우 데이터 패키지 생성 |
| | `POST` | `/api/dashboard/export/docs` | 🔑 | AI 분석 Markdown 기반 문서 내용 및 리포트 데이터 반환 (Google Docs 미사용) |

### 3. 리뷰 및 제품 분석 (리뷰분석 / 제품관리)
| 태그 | 메서드 | 엔드포인트 | 인증 | 설명 |
| :--- | :--- | :--- | :---: | :--- |
| **Reviews** | `GET` | `/api/reviews/count` | 🔑 | 필터 조건별 리뷰 총 건수 조회 (병렬 청크 로딩용) |
| | `GET` | `/api/reviews` | 🔑 | 통합 검색 및 다중 조건 필터링 페이징 리뷰 목록 조회 |
| | `GET` | `/api/reviews/attribute-scores` | 🔑 | 스킨케어 3대 품질 속성 점수 종합 기간 평균 수치 산출 |
| | `POST` | `/api/reviews/export` | 🔑 | 현재 필터링된 모든 리뷰를 BOM-UTF8 프리미엄 CSV 스트림 전송 |
| | `POST` | `/api/reviews/bulk` | ❌ | 크롤링 원시 데이터 대량 업로드 및 AI ABSA 파이프라인 적재 |
| **Products** | `GET` | `/api/products/stats` | 🔑 | 등록 제품 수, 분석 활성 제품 수, 누적 리뷰 집계 조회 |
| | `GET` | `/api/products` | 🔑 | 정렬, 검색 및 페이징이 가미된 전체 상품 관리 목록 조회 |
| | `GET` | `/api/products/list` | ❌ | 프론트엔드 필터용 전체 단순 제품 드롭다운 리스트 반환 |
| | `POST` | `/api/products` | 🔑 | 신규 화장품 제품 등록 (브랜드, 피부타입 등 관계 자동 등록) |
| | `PATCH` | `/api/products/{id}` | 🔑 | 분석 활성화 토글(`is_analysis_active`) 및 제품 정보 부분 갱신 |
| | `POST` | `/api/products/sync` | 🔑 | 크롤러 엔진 수동 배치 동기화 시작 및 이력 상태 기록 |

### 4. AI 어시스턴트 및 제어센터 (Layout & Control Center)
| 태그 | 메서드 | 엔드포인트 | 인증 | 설명 |
| :--- | :--- | :--- | :---: | :--- |
| **Layout** | `GET` | `/api/layout` | 🔑 | 사용자별 대시보드 고정(핀) 위젯 레이아웃 조회 |
| | `PUT` | `/api/layout` | 🔑 | 사용자별 대시보드 고정(핀) 위젯 레이아웃 영속 저장/수정 |
| **AI Assistant**| `POST` | `/api/ai/chat` | 🔑 | pgvector 시맨틱 컨텍스트 매칭 결합 RAG 챗봇 어시스턴트 대화 |
| | `GET` | `/api/ai/insight-briefing`| 🔑 | 리뷰 분석용 실시간 AI 핵심 VOC 요약 브리핑 및 현황 조회 |
| **Admin** | `GET` | `/api/admin/users` | 🔑(S) | 제어센터 - 전체 관리자 계정 목록 조회 (슈퍼 관리자 권한 필수) |
| | `POST` | `/api/admin/users` | 🔑(S) | 제어센터 - B2B 신규 관리자 계정 생성 (슈퍼 관리자 권한 필수) |
| | `PATCH` | `/api/admin/users/{id}` | 🔑(S) | 제어센터 - 관리자 권한/상태/비밀번호 부분 수정 (슈퍼 관리자 권한) |
| | `DELETE`| `/api/admin/users/{id}` | 🔑(S) | 제어센터 - 관리자 계정 영구 삭제 (슈퍼 관리자 권한 필수) |
| **Settings** | `GET` | `/api/settings` | 🔑 | 제어센터 - 알림 및 시스템 환경 설정값 조회 |
| | `PUT` | `/api/settings` | 🔑 | 제어센터 - 알림 및 시스템 환경 설정값 수정/저장 |
| | `POST` | `/api/settings/reset` | 🔑 | 제어센터 - 알림 및 환경 설정을 팩토리 초기화 상태로 복원 |
| **Integrations**| `GET` | `/api/integrations/status`| 🔑 | 제어센터 - 네이버·올리브영 연동 플랫폼 이력 및 상태 정보 조회 |

* 🔑 : JWT Bearer 인증 필수  
* 🔑(S) : JWT Bearer 인증 필수 및 `super_admin` 권한 검증 미들웨어 필요  
* ❌ : 인증 불필요  

---

## 🔒 상세 API 규격서

### 1. Health & Auth (서버 상태 및 인증)

#### `GET /health`
- **설명**: 백엔드 API 서버의 생존 여부 및 가동 프로젝트 상태를 반환한다.
- **인증**: ❌
- **Response** (200 OK):
  ```json
  {
    "status": "healthy",
    "project": "TONES Server",
    "version": "1.0.0"
  }
  ```

#### `POST /api/auth/login`
- **설명**: JSON 요청 본문을 수신하여 이메일과 비밀번호를 검증하고 JWT 토큰을 발급하며, 사용자의 `last_login_at` 시간 값을 실시간 갱신한다.
- **인증**: ❌
- **Request Body** (application/json):
  ```json
  {
    "email": "test@example.com",
    "password": "testpassword"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiw...",
    "token_type": "bearer"
  }
  ```
- **Error Response** (400 Bad Request):
  ```json
  { "detail": "이메일 또는 비밀번호가 잘못되었습니다." }
  ```

#### `POST /api/auth/login/access-token`
- **설명**: FastAPI Docs 및 OAuth2 표준을 따르는 폼 데이터 기반의 액세스 토큰 발급/로그인 API이다.
- **인증**: ❌
- **Request Body** (multipart/form-data):
  - `username` (string, required): 이메일 주소
  - `password` (string, required): 비밀번호
- **Response** (200 OK):
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
  }
  ```

#### `POST /api/auth/logout`
- **설명**: 세션 파기 및 로그아웃 성공 메시지를 반환한다. (클라이언트 토큰 제거 유도)
- **인증**: ❌
- **Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "성공적으로 로그아웃되었습니다."
  }
  ```

#### `POST /api/auth/signup`
- **설명**: B2B 플랫폼 신규 사용자의 회원가입을 처리한다.
- **인증**: ❌
- **Request Body** (application/json):
  ```json
  {
    "email": "user@example.com",
    "password": "userpassword",
    "full_name": "홍길동",
    "role": "manager"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "email": "user@example.com",
    "full_name": "홍길동",
    "is_active": true,
    "role": "manager",
    "last_login_at": null,
    "id": "user-uuid-123"
  }
  ```
- **Error Response** (400 Bad Request):
  ```json
  { "detail": "이미 존재하는 이메일입니다." }
  ```

#### `POST /api/auth/find-email`
- **설명**: 가입된 이름(full_name) 정보를 기반으로 이메일을 조회한다.
- **인증**: ❌
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
- **Error Response** (404 Not Found):
  ```json
  { "detail": "해당 이름으로 등록된 사용자를 찾을 수 없습니다." }
  ```

#### `POST /api/auth/find-password`
- **설명**: 이메일과 이름이 일치하는 사용자를 식별하여 임시 패스워드를 재설정 및 발급한다.
- **인증**: ❌
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
    "temp_password": "temp-pass-abc-123"
  }
  ```
- **Error Response** (404 Not Found):
  ```json
  { "detail": "이메일과 이름이 일치하는 사용자를 찾을 수 없습니다." }
  ```

#### `GET /api/users/me`
- **설명**: 로그인된 사용자의 권한(`role`) 및 상세 프로필 정보를 조회한다.
- **인증**: 🔑
- **Response** (200 OK):
  ```json
  {
    "email": "test@example.com",
    "full_name": "Test User",
    "is_active": true,
    "role": "super_admin",
    "last_login_at": "2026-06-02T15:20:16.123Z",
    "id": "user_12345"
  }
  ```

---

### 2. Dashboard (홈 대시보드 분석)

#### `GET /api/dashboard/summary`
- **설명**: 기간 및 제품 필터를 조합하여 전체 리뷰 수, 평균 별점, 부정 리뷰 비율 및 WoW 변동량, 우선 확인 부정 리뷰 요약을 반환한다.
- **인증**: 🔑
- **Query Parameters**:
  - `product_id` (string, optional): 특정 제품 UUID (미지정 시 전체 상품 합산)
  - `period` (integer, default=7): 분석 기간 범위 (일)
- **Response** (200 OK):
  ```json
  {
    "total_reviews": 125,
    "total_reviews_diff": 12,
    "average_rating": 4.12,
    "average_rating_diff": 0.15,
    "negative_reviews_count": 22,
    "negative_reviews_rate": 17.6,
    "negative_reviews_rate_diff": -2.4,
    "urgent_reviews_summary": [
      {
        "id": "rev-uuid-101",
        "summary": "리뉴얼된 패드 사용 후 이마에 여드름이 뒤집어졌다는 불만 제기",
        "rating": 1
      }
    ]
  }
  ```

#### `GET /api/dashboard/trending-keywords`
- **설명**: 분석 기간 내 수집된 리뷰에서 언급 빈도가 가장 높은 상위 5대 급상승 키워드를 추출한다.
- **인증**: 🔑
- **Query Parameters**:
  - `product_id` (string, optional): 특정 제품 UUID
  - `period` (integer, default=7): 분석 기간 범위 (일)
- **Response** (200 OK):
  ```json
  [
    { "keyword": "자극", "count": 48 },
    { "keyword": "수분감", "count": 35 },
    { "keyword": "진정", "count": 29 },
    { "keyword": "용기불량", "count": 22 },
    { "keyword": "끈적임", "count": 19 }
  ]
  ```

#### `GET /api/dashboard/negative-trend`
- **설명**: Recharts 시계열 꺾은선/막대 차트 연동을 위한 일자별 부정 리뷰 발생 카운트 리스트를 오름차순 반환한다.
- **인증**: 🔑
- **Query Parameters**:
  - `product_id` (string, optional): 특정 제품 UUID
  - `period` (integer, default=7): 분석 기간 범위 (일)
- **Response** (200 OK):
  ```json
  [
    { "date": "2026-05-27", "count": 2 },
    { "date": "2026-05-28", "count": 5 },
    { "date": "2026-05-29", "count": 3 },
    { "date": "2026-05-30", "count": 0 },
    { "date": "2026-05-31", "count": 4 }
  ]
  ```

#### `GET /api/dashboard/insights`
- **설명**: 화장품 3대 주요 VOC 만족도(성분진정, 제형흡수, 용기편의) 백분율 점수 및 전주 대비 증감폭(%p)을 가져온다. Top 5 급상승 키워드 중 해당 카테고리와 연관된 키워드 목록(언급 횟수 포함)이 `related_keywords`에 함께 반환된다.
- **인증**: 🔑
- **Query Parameters**:
  - `product_id` (string, optional): 특정 제품 UUID
  - `period` (integer, default=7): 분석 기간 범위 (일)
- **Response** (200 OK):
  ```json
  {
    "ingredients": {
      "label": "성분 및 피부 진정",
      "score": 88.5,
      "change": 3.2,
      "change_description": "+3.2%p 개선",
      "sentiment": "positive",
      "related_keywords": [
        { "keyword": "자극", "count": 48 },
        { "keyword": "진정", "count": 29 }
      ],
      "insight_text": "급상승 키워드 '자극'(48회), '진정'(29회)가 성분·피부 진정 관련 이슈와 연관됩니다. (+3.2%p)"
    },
    "formulation": {
      "label": "제형 흡수력 및 발림성",
      "score": 92.0,
      "change": 1.5,
      "change_description": "+1.5%p 개선",
      "sentiment": "positive",
      "related_keywords": [
        { "keyword": "끈적임", "count": 19 }
      ],
      "insight_text": "제형·발림성 관련 만족도가 전기 대비 +1.5%p 개선되었습니다."
    },
    "container": {
      "label": "용기 불량 및 편리성",
      "score": 64.2,
      "change": -8.4,
      "change_description": "-8.4%p 하락",
      "sentiment": "negative",
      "related_keywords": [
        { "keyword": "용기불량", "count": 22 }
      ],
      "insight_text": "급상승 키워드 '용기불량'(22회)가 용기·편의성 관련 불만 반응과 연관됩니다. 만족도 -8.4%p 하락했습니다."
    }
  }
  ```

#### `GET /api/dashboard/ai-briefing`
- **설명**: 지정 기간 및 제품 기준 Gemini 2.0 기반으로 실시간 대시보드 VOC 분석 트렌드 요약 브리핑 텍스트를 구성하여 반환한다.
- **인증**: 🔑
- **Query Parameters**:
  - `product_id` (string, optional): 특정 제품 UUID
  - `period` (integer, default=7): 분석 기간 범위 (일)
- **Response** (200 OK):
  ```json
  {
    "ai_briefing": "최근 7일간 전체 리뷰 분석 결과, 수분 진정에 대한 만족도는 증가했으나 용기 불량 및 뚜껑 헛돎 관련 불만이 발생했습니다..."
  }
  ```

#### `POST /api/dashboard/report`
- **설명**: 요약 및 인사이트, 키워드를 결합한 정규 AI 대시보드 종합 성과 리포트 파일(Markdown 본문) 및 로우 통계 데이터 객체를 동적 빌드하여 제공한다.
- **인증**: 🔑
- **Query Parameters**:
  - `product_id` (string, optional): 특정 제품 UUID
  - `period` (integer, default=7): 분석 기간 범위 (일)
  - `report_type` (string, default="general"): 리포트 종류 명세
- **Response** (200 OK):
  ```json
  {
    "success": true,
    "report_id": "rep_1740929281",
    "report_markdown": "# TONES AI 분석 보고서\n\n- **생성시점**: 2026-06-02 15:35:00\n- **분석기간**: 최근 7일\n...\n",
    "raw_data": {
      "summary": { },
      "insights": { },
      "keywords": [ ]
    }
  }
  ```

#### `POST /api/dashboard/export/docs`
- **설명**: 대시보드의 AI 분석 요약 데이터(Markdown)를 구성하여 프론트엔드로 직접 마크다운 본문을 반환한다. (Google Docs API는 사용하지 않음)
- **인증**: 🔑
- **Request Body** (application/json):
  ```json
  {
    "title": "2026-06 화장품 VOC AI 분석 리포트",
    "period": 30,
    "product_id": "all",
    "report_markdown": "# TONES AI 분석 보고서\n\n- **생성시점**: 2026-06-02...\n (미리 생성된 마크다운, 생략 시 자동 구성)"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "리포트 마크다운이 성공적으로 생성되었습니다.",
    "document_id": null,
    "document_url": null,
    "report_markdown": "# TONES AI 분석 보고서\n\n- **생성시점**: 2026-06-04..."
  }
  ```

---

### 3. Reviews (리뷰 분석 및 제어)

#### `GET /api/reviews/count`
- **설명**: 현재 필터 조건(제품, 기간, 감성, 검색어)에 해당하는 리뷰 총 건수를 반환한다. 프론트엔드의 병렬 청크 로딩 시 총 청크 수 계산에 사용된다.
- **인증**: 🔑
- **Query Parameters**:
  - `product` (string, optional): 제품 UUID
  - `period` (integer, optional): 분석 기간 (일)
  - `sentiment` (string, optional): 감성 구분 (`positive`, `neutral`, `negative`)
  - `q` (string, optional): 검색어 (리뷰 본문 LIKE 검색)
  - `priority` (boolean, default=false): `true` 설정 시 우선 확인 리뷰(`sentiment=negative AND rating≤2`)만 집계. `sentiment` 파라미터보다 우선 적용됨
- **Response** (200 OK):
  ```json
  {
    "total": 2150
  }
  ```

#### `GET /api/reviews`
- **설명**: 다중 필터링 조건 및 검색어가 결합된 고성능 동적 쿼리 페이징 리뷰 리스트를 반환한다. (GCP Cloud SQL PostgreSQL 최적화 작동)
- **인증**: 🔑
- **Query Parameters**:
  - `product` (string, optional): 제품 UUID
  - `period` (integer, optional): 분석 기간 (일)
  - `sentiment` (string, optional): 감성 구분 (`positive`, `neutral`, `negative`)
  - `q` (string, optional): 검색어 (리뷰 본문 LIKE 검색)
  - `priority` (boolean, default=false): `true` 설정 시 우선 확인 리뷰(`sentiment=negative AND rating≤2`)만 반환. `sentiment` 파라미터보다 우선 적용됨
  - `page` (integer, default=1): 페이지 번호
  - `limit` (integer, default=20): 한 페이지 크기
- **Response** (200 OK):
  ```json
  [
    {
      "id": "rev-uuid-555",
      "product_id": "e680f731-cfde-427f-9077-62f7e484ec21",
      "source": "olive_young",
      "reviewer_type": "민감성 피부",
      "review_text": "패드가 정말 도톰하고 밀착력이 좋은데, 제형은 끈적임 없이 금방 흡수돼서 아침 토너용으로 쓰기 편해요.",
      "rating": 5,
      "review_date": "2026-06-01",
      "sentiment": "positive",
      "sentiment_score": 0.94,
      "keywords": ["도톰", "밀착력", "끈적임", "아침토너"],
      "issue_type": "없음",
      "ai_summary": "도톰한 패드의 높은 밀착력과 산뜻하게 흡수되는 끈적임 없는 제형에 높은 만족을 보임.",
      "score_ingredients": 0.85,
      "score_formulation": 0.92,
      "score_container": 0.50,
      "review_id": "rev_ext_999202"
    }
  ]
  ```

#### `GET /api/reviews/attribute-scores`
- **설명**: 스킨케어 3대 품질 속성(성분/피부, 제형/발림성, 용기/디자인) 평균 점수를 산출하여 반환한다.
- **인증**: 🔑
- **Query Parameters**:
  - `product` (string, optional): 제품 UUID
  - `period` (integer, optional): 분석 기간 (일)
- **Response** (200 OK):
  ```json
  {
    "score_ingredients": 0.88,
    "score_formulation": 0.92,
    "score_container": 0.64
  }
  ```

#### `POST /api/reviews/export`
- **설명**: 현재 쿼리 및 필터에 정합하는 모든 리뷰 데이터를 정형화하여 BOM 헤더가 포함된 엑셀/Windows OS 완벽 호환 `utf-8-sig` 바이트 CSV 파일 다운로드 파일 스트림을 반환한다.
- **인증**: 🔑
- **Response**: `text/csv` 바이너리 스트림 파일 전송 (다운로드 파일명: `tones_reviews_export.csv`)

#### `POST /api/reviews/bulk`
- **설명**: 수집된 원시 리뷰 데이터를 대량으로 수신하고, 각 리뷰에 대해 ABSA(속성 기반 감성 분석) 및 AI 분석 파이프라인 처리를 수행하여 DB에 적재한다.
- **인증**: ❌
- **Request Body** (application/json, List):
  ```json
  [
    {
      "product_id": "e680f731-cfde-427f-9077-62f7e484ec21",
      "content": "이 패드 진짜 자극 없고 촉촉해요.",
      "rating": 5,
      "skin_type": "건성",
      "reviewer_type": "건성 피부",
      "source": "올리브영",
      "review_date": "2026-06-03",
      "review_id": "rev_ext_12345"
    }
  ]
  ```
- **Response** (201 Created):
  ```json
  {
    "success": true,
    "message": "1건의 리뷰 처리가 정상 완료되었습니다.",
    "processed_count": 1,
    "saved_count": 1
  }
  ```

---

### 4. Products (제품 및 동기화 제어)

#### `GET /api/products/stats`
- **설명**: 제품 관리 전반에 관한 통계(등록된 전체 제품 수, 분석 활성 제품 수, 누적 리뷰 집계 수)를 반환한다.
- **인증**: 🔑
- **Response** (200 OK):
  ```json
  {
    "total_products": 10,
    "active_products": 8,
    "total_reviews": 5420
  }
  ```

#### `GET /api/products`
- **설명**: 정렬, 검색 및 페이징이 가미된 전체 상품 관리 목록을 반환한다.
- **인증**: 🔑
- **Query Parameters**:
  - `q` (string, optional): 검색어 (브랜드명 또는 상품명 검색)
  - `sort` (string, default="name"): 정렬 조건
  - `page` (integer, default=1)
  - `limit` (integer, default=10)
- **Response** (200 OK):
  ```json
  {
    "items": [
      {
        "id": "e680f731-cfde-427f-9077-62f7e484ec21",
        "brand_name": "스킨푸드",
        "product_name": "캐롯 카로틴 카밍 워터 패드",
        "category": "pad",
        "target_skin": "민감성",
        "is_analysis_active": true,
        "price": 26000.0,
        "created_at": "2026-06-02T10:00:00Z",
        "review_count": 1250
      }
    ],
    "total": 1,
    "page": 1,
    "limit": 10
  }
  ```

#### `GET /api/products/list`
- **설명**: 프론트엔드 필터용 전체 단순 제품 드롭다운 리스트를 반환한다.
- **인증**: ❌
- **Response** (200 OK):
  ```json
  [
    {
      "id": "e680f731-cfde-427f-9077-62f7e484ec21",
      "brand_name": "스킨푸드",
      "product_name": "캐롯 카로틴 카밍 워터 패드",
      "category": "pad",
      "target_skin": "민감성",
      "created_at": "2026-06-02T10:00:00Z"
    }
  ]
  ```

#### `POST /api/products`
- **설명**: 신규 화장품 상품을 등록하며, 테이블 내에 존재하지 않는 신규 브랜드/카테고리/피부타입이 감지될 경우 단일 트랜잭션 원자성을 통해 Lookup 테이블에 선행 자동 삽입 매핑을 처리한다.
- **인증**: 🔑
- **Request Body** (application/json):
  ```json
  {
    "brand_name": "라운드랩",
    "product_name": "자작나무 수분 선크림 패드",
    "description": "산뜻하고 촉촉한 자작나무 수액 함유 자외선 차단 선패드",
    "price": 28000.0,
    "category": "pad",
    "target_skin": "민감성"
  }
  ```
- **Response** (201 Created):
  ```json
  {
    "success": true,
    "product": {
      "id": "new-prod-uuid-888",
      "brand_name": "라운드랩",
      "product_name": "자작나무 수분 선크림 패드",
      "description": "산뜻하고 촉촉한 자작나무 수액 함유 자외선 차단 선패드",
      "price": 28000.0,
      "category": "pad",
      "target_skin": "민감성",
      "is_analysis_active": true
    }
  }
  ```

#### `PATCH /api/products/{id}`
- **설명**: 등록된 제품의 메타데이터를 수정하거나 분석 주기 포함 활성화 토글 필드(`is_analysis_active`) 상태를 갱신한다.
- **인증**: 🔑
- **Request Body**:
  ```json
  {
    "is_analysis_active": false
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "success": true,
    "product_id": "new-prod-uuid-888",
    "is_analysis_active": false
  }
  ```

#### `POST /api/products/sync`
- **설명**: 외부 쇼핑몰 플랫폼(네이버, 올리브영) 스크래퍼 크롤링 파이프라인 엔진 수동 가동 신호를 송출하고, `integrations` 동기화 이력 DB를 실시간 갱신한다.
- **인증**: 🔑
- **Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "크롤링 배치 엔진 동기화가 성공적으로 시작되어 정상 반영되었습니다.",
    "platforms": ["naver", "olive_young"]
  }
  ```

---

### 5. Control Center & AI (제어센터 및 AI 어시스턴트)

#### `GET /api/layout`
- **설명**: 사용자별 대시보드 고정(핀) 위젯 레이아웃 정보를 조회한다.
- **인증**: 🔑
- **Query Parameters**:
  - `token` (string, required): 사용자 식별 토큰
- **Response** (200 OK):
  ```json
  {
    "pinned_widget": "negative-trend"
  }
  ```

#### `PUT /api/layout` / `POST /api/layout`
- **설명**: 사용자별 대시보드 고정(핀) 위젯 레이아웃 정보를 영속 저장하거나 수정한다. (POST는 프론트엔드 호환용)
- **인증**: 🔑
- **Request Body** (application/json):
  ```json
  {
    "token": "user-token-abc",
    "pinned_widget": "trending-keywords"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "success": true
  }
  ```

#### `POST /api/ai/search`
- **설명**: pgvector 확장 코사인 유사도 검색을 이용한 벡터 DB 내 유사 리뷰 시맨틱 검색을 수행한다.
- **인증**: 🔑
- **Request Body** (application/json):
  ```json
  {
    "query": "패드 밀착력",
    "top_k": 3,
    "filter": {
      "product_id": "e680f731-cfde-427f-9077-62f7e484ec21"
    }
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "query": "패드 밀착력",
    "results": [
      {
        "id": "rev-uuid-123",
        "score": 0.1245,
        "metadata": {
          "review_text": "패드가 피부에 엄청 밀착이 잘 되네요.",
          "rating": 5,
          "sentiment": "positive"
        }
      }
    ]
  }
  ```

#### `POST /api/ai/generate`
- **설명**: 전달받은 텍스트 요약 컨텍스트와 질문 프롬프트를 이용하여 AI 단독 답변을 빌드한다.
- **인증**: 🔑
- **Request Body** (application/json):
  ```json
  {
    "prompt": "해당 제품의 밀착력에 대한 요약은?",
    "context": "[평점: 5] 리뷰 내용: 패드가 피부에 엄청 밀착이 잘 되네요."
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "answer": "해당 제품은 패드의 높은 피부 밀착력 측면에서 긍정적인 평가를 받고 있습니다."
  }
  ```

#### `POST /api/ai/chat`
- **설명**: 사용자의 어시스턴트 질문(질의)에 맞춰, pgvector 확장 코사인 유사도 검색(`<=>`)을 구동해 정합하는 고객 리뷰 본문을 RAG 컨텍스트로 취합한 후 Gemini 2.0 비동기 챗 답변과 레퍼런스 증거 데이터 목록을 실시간 조립하여 반환한다. (3단계 3중 강건성 폴백 보장)
- **인증**: 🔑
- **Request Body** (application/json):
  ```json
  {
    "message": "당근패드 용기 뚜껑에 대한 불만이 주로 뭐야?",
    "product_id": "04472697-d7c5-4cbe-bbc1-3cb62d3d4eba"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "answer": "검색된 당근패드 고객 리뷰 분석 결과, 주로 용기 집게 보관 캡의 헐거움과 뚜껑을 닫을 때 나사선이 잘 맞지 않아 헛도는 결함에 대한 불만이 뚜렷하게 관찰되고 있습니다. 주요 참고 리뷰는...",
    "referenced_reviews": [
      {
        "id": "rev_5",
        "score": 0.941,
        "review_text": "용기가 너무 불편해요!! 뚜껑 헛돌고 집게 보관 캡이 헐거워져 아래로 빠집니다.",
        "rating": 2,
        "sentiment": "negative",
        "ai_summary": "뚜껑 헛돌기와 내부 집게 보관 캡 이탈 등 용기 품질 불만 토로"
      }
    ]
  }
  ```

#### `GET /api/ai/insight-briefing`
- **설명**: 리뷰 분석을 위한 실시간 AI 핵심 VOC 요약 브리핑 및 현황 통계 정보를 단일 요청으로 조회한다.
- **인증**: 🔑
- **Query Parameters**:
  - `product_id` (string, optional): 특정 제품 필터 ID
  - `period` (integer, default=7): 조회할 기간 범위 (일)
- **Response** (200 OK):
  ```json
  {
    "insight_briefing": "최근 7일간 수집된 전체 리뷰의 3대 품질 속성 및 만족도는...",
    "total_reviews": 125,
    "average_rating": 4.12,
    "attribute_scores": {
      "score_ingredients": 0.88,
      "score_formulation": 0.92,
      "score_container": 0.64
    }
  }
  ```

#### `GET /api/admin/users`
- **설명**: 제어센터의 등록된 전체 관리자 계정 목록을 반환한다. (슈퍼 관리자 권한 필수)
- **인증**: 🔑(S)
- **Response** (200 OK):
  ```json
  [
    {
      "id": "admin-uuid-1",
      "email": "admin@tones.com",
      "full_name": "관리자",
      "role": "manager",
      "is_active": true,
      "last_login_at": "2026-06-03T18:00:00Z"
    }
  ]
  ```

#### `POST /api/admin/users`
- **설명**: 제어센터 내 신규 B2B 관리자 계정을 강제 등록 생성한다. (슈퍼 관리자 권한 필수)
- **인증**: 🔑(S)
- **Request Body** (application/json):
  ```json
  {
    "email": "manager2@tones.com",
    "full_name": "박매니저",
    "password": "managerpassword",
    "role": "manager"
  }
  ```
- **Response** (201 Created):
  ```json
  {
    "id": "admin-uuid-2",
    "email": "manager2@tones.com",
    "full_name": "박매니저",
    "role": "manager",
    "is_active": true,
    "last_login_at": null
  }
  ```

#### `PATCH /api/admin/users/{id}`
- **설명**: 특정 관리자 계정 정보(역할, 활성화 여부, 비밀번호 등)를 부분 수정한다. (슈퍼 관리자 권한 필수)
- **인증**: 🔑(S)
- **Request Body** (application/json):
  ```json
  {
    "full_name": "수정박매니저",
    "role": "analyst",
    "is_active": false
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "id": "admin-uuid-2",
    "email": "manager2@tones.com",
    "full_name": "수정박매니저",
    "role": "analyst",
    "is_active": false,
    "last_login_at": null
  }
  ```

#### `DELETE /api/admin/users/{id}`
- **설명**: 특정 B2B 관리자 계정을 영구 삭제한다. (슈퍼 관리자 권한 필수)
- **인증**: 🔑(S)
- **Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "계정이 정상적으로 영구 삭제되었습니다."
  }
  ```

#### `GET /api/settings`
- **설명**: 알림 및 시스템 환경 설정값을 DB에서 조회하여 반환한다.
- **인증**: 🔑
- **Response** (200 OK):
  ```json
  {
    "notification_enabled": true,
    "dark_mode": false,
    "analysis_interval_hours": 24
  }
  ```

#### `PUT /api/settings`
- **설명**: 알림 여부, 다크 모드, 수집 분석 주기 등 시스템 설정 레코드를 수정한다.
- **인증**: 🔑
- **Request Body** (application/json):
  ```json
  {
    "notification_enabled": false,
    "dark_mode": true,
    "analysis_interval_hours": 12
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "설정이 성공적으로 저장되었습니다."
  }
  ```

#### `GET /api/integrations/status`
- **설명**: 네이버 쇼핑 스토어 및 올리브영 데이터 수집 연동 에이전트의 배치 작동 상태 및 에러 코드를 DB에서 조회해 반환한다.
- **인증**: 🔑
- **Response** (200 OK):
  ```json
  [
    {
      "platform_name": "naver",
      "status": "connected",
      "sync_rate": 98.0,
      "error_message": null,
      "last_synced_at": "2026-06-02T15:20:16Z"
    },
    {
      "platform_name": "olive_young",
      "status": "error",
      "sync_rate": 40.0,
      "error_message": "408 Request Timeout",
      "last_synced_at": "2026-06-02T10:15:30Z"
    }
  ]
  ```

#### `POST /api/settings/reset`
- **설명**: 제어센터의 시스템 설정 테이블(Settings) 레코드를 공장 초기화 설정(알림 수신 ON, 라이트 모드 기본, 동기화 주기 24시간)으로 복원한다.
- **인증**: 🔑
- **Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "모든 시스템 환경 설정이 기본값으로 초기화되었습니다."
  }
  ```

