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
- **설명**: 백엔드 API 서버의 생존 여부 및 가동 프로젝트 상태를 리턴합니다.
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
- **설명**: JSON 요청 본문을 수신하여 이메일과 비밀번호를 검증하고 JWT 토큰을 발급하며, 사용자의 `last_login_at` 시간 값을 실시간 갱신합니다.
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
- **설명**: FastAPI Docs 및 OAuth2 표준을 따르는 폼 데이터 기반의 액세스 토큰 발급/로그인 API입니다.
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
- **설명**: 세션 파기 및 로그아웃 성공 메시지를 반환합니다. (클라이언트 토큰 제거 유도)
- **인증**: ❌
- **Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "성공적으로 로그아웃되었습니다."
  }
  ```

#### `GET /api/users/me`
- **설명**: 로그인된 사용자의 권한(`role`) 및 최종 로그인 시간(`last_login_at`)이 포함된 프로필 정보를 조회합니다.
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
- **설명**: 기간 및 제품 필터를 조합하여 요약 지표 및 전주 대비 증감폭(WoW), 그리고 긴급하게 대응해야 할 부정 리뷰 3건의 간략 요약 어레이를 서빙합니다.
- **인증**: 🔑
- **Query Parameters**:
  - `product_id` (string, optional): 특정 제품 UUID
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
- **설명**: 분석 기간 내 수집된 리뷰에서 언급 빈도가 가장 높은 상위 5대 급상승 키워드를 추출합니다.
- **인증**: 🔑
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
- **설명**: Recharts 시계열 꺾은선/막대 차트 연동을 위한 일자별 부정 리뷰 발생 카운트 리스트를 오름차순 반환합니다.
- **인증**: 🔑
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
- **설명**: 화장품 3대 주요 VOC 만족도(성분진정, 제형흡수, 용기편의) 백분율 점수 및 전주 대비 증감폭(%p)을 가져옵니다.
- **인증**: 🔑
- **Response** (200 OK):
  ```json
  {
    "ingredients": { "score": 88.5, "change": 3.2 },
    "formulation": { "score": 92.0, "change": 1.5 },
    "container": { "score": 64.2, "change": -8.4 }
  }
  ```

#### `POST /api/dashboard/report`
- **설명**: 요약 및 인사이트, 키워드를 결합한 정규 AI 대시보드 종합 성과 리포트 파일(Markdown 본문) 및 로우 통계 데이터 객체를 동적 빌드하여 제공합니다.
- **인증**: 🔑
- **Response** (200 OK):
  ```json
  {
    "success": true,
    "report_id": "rep_1740929281",
    "report_markdown": "# TONES AI 분석 보고서\n\n- **생성시점**: 2026-06-02 15:35:00\n- **분석기간**: 최근 7일\n...\n",
    "raw_data": {
      "summary": { ... },
      "insights": { ... },
      "keywords": [ ... ]
    }
  }
  ```

---

### 3. Reviews (리뷰 분석 및 제어)

#### `GET /api/reviews/count`
- **설명**: 현재 필터 조건(제품, 기간, 감성, 검색어)에 해당하는 리뷰 총 건수를 반환합니다. 프론트엔드의 병렬 청크 로딩 시 총 청크 수 계산에 사용됩니다.
- **인증**: 🔑
- **Query Parameters**:
  - `product` (string, optional): 제품 UUID
  - `period` (integer, optional): 분석 기간 (일)
  - `sentiment` (string, optional): 감성 구분 (`positive`, `neutral`, `negative`)
  - `q` (string, optional): 검색어 (리뷰 본문 LIKE 검색)
- **Response** (200 OK):
  ```json
  {
    "total": 2150
  }
  ```

#### `GET /api/reviews`
- **설명**: 다중 필터링 조건 및 검색어가 결합된 고성능 동적 쿼리 페이징 리뷰 리스트를 반환합니다. (GCP Cloud SQL PostgreSQL 최적화 작동)
- **인증**: 🔑
- **Query Parameters**:
  - `product` (string, optional): 제품 UUID
  - `period` (integer, optional): 분석 기간 (일)
  - `sentiment` (string, optional): 감성 구분 (`positive`, `neutral`, `negative`)
  - `q` (string, optional): 검색어 (리뷰 본문 LIKE 검색)
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

#### `POST /api/reviews/export`
- **설명**: 현재 쿼리 및 필터에 정합하는 모든 리뷰 데이터를 정형화하여 BOM 헤더가 포함된 엑셀/Windows OS 완벽 호환 `utf-8-sig` 바이트 CSV 파일 다운로드 파일 스트림을 뿜어냅니다.
- **인증**: 🔑
- **Response**: `text/csv` 바이너리 스트림 파일 전송 (다운로드 파일명: `tones_reviews_export.csv`)

---

### 4. Products (제품 및 동기화 제어)

#### `POST /api/products`
- **설명**: 신규 화장품 상품을 등록하며, 테이블 내에 존재하지 않는 신규 브랜드/카테고리/피부타입이 감지될 경우 단일 트랜잭션 원자성을 통해 Lookup 테이블에 선행 자동 삽입 매핑을 안전하게 처리합니다.
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
- **설명**: 등록된 제품의 메타데이터를 수정하거나 분석 주기 포함 활성화 토글 필드(`is_analysis_active`) 상태를 갱신합니다.
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
- **설명**: 외부 쇼핑몰 플랫폼(네이버, 올리브영) 스크래퍼 크롤링 파이프라인 엔진 수동 가동 신호를 송출하고, `integrations` 동기화 이력 DB를 실시간 갱신합니다.
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

#### `POST /api/ai/chat`
- **설명**: 사용자의 어시스턴트 질문(질의)에 맞춰, pgvector 확장 코사인 유사도 검색(`<=>`)을 구동해 정합하는 고객 리뷰 본문을 RAG 컨텍스트로 취합한 후 Gemini 2.0 비동기 챗 답변과 레퍼런스 증거 데이터 목록을 실시간 조립하여 리턴합니다. (3단계 3중 강건성 폴백 보장)
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

#### `GET /api/integrations/status`
- **설명**: 네이버 쇼핑 스토어 및 올리브영 데이터 수집 연동 에이전트의 배치 작동 상태 및 에러 코드를 DB를 단순 조회(배치 기록 연동)해 가장 가볍고 효율적으로 반환합니다.
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
- **설명**: 제어센터의 시스템 설정 테이블(Settings) 레코드를 공장 초기화 설정(알림 수신 ON, 라이트 모드 기본, 동기화 주기 24시간)으로 리셋 업데이트합니다.
- **인증**: 🔑
- **Response** (200 OK):
  ```json
  {
    "success": true,
    "message": "모든 시스템 환경 설정이 기본값으로 초기화되었습니다."
  }
  ```
