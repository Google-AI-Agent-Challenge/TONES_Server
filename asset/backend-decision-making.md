# 📋 백엔드 기술 의사결정 문서 (Decision Making)

우리 프로젝트의 **백엔드 기술 의사결정** 문서에 오신 것을 환영합니다. 이 문서는 고성능의 견고한 백엔드 시스템을 정의하는 기술적 맥락, 주요 아키텍처 결정 사항 및 디렉터리 구조를 설명합니다.

---

## 🛠️ 백엔드 개발 환경 및 기술 스택 (Context)

우리의 백엔드 스택은 Python 3.11+ 에코시스템과 FastAPI 비동기 프레임워크를 기반으로 구축되었으며, 벡터 데이터베이스, 실시간 AI 에이전트, 자가 치유(Self-Healing) 파이프라인 및 엔드투엔드 보안 미들웨어가 설계되어 있습니다.

| 구분 | 기술 스택 | 주요 상세 정보 및 버전 |
| :--- | :--- | :--- |
| **핵심 웹/프레임워크** | **FastAPI 0.110.0+** | Python 3.11+ 기반의 고성능 비동기 API 웹 프레임워크 설계 |
| **언어** | **Python Type Hints** | 안정적이고 견고한 정적 분석 기반 타이핑 환경 구축 |
| **비동기 WAS** | **Uvicorn standard 0.28.0+** | 고성능 비동기 ASGI 서버 구동 및 실시간 이벤트 동시성 제어 |
| **데이터 레이어** | **GCP Cloud SQL & pgvector** | `pg8000` 비동기 직접 드라이버 및 `pgvector 0.2.0+` 패키지를 도입하여 PostgreSQL 내 코사인 유사도 연산 및 시맨틱 RAG 통합 검색 구현 (구형 Pinecone 벡터 DB 의존성 전면 제거) |
| **AI 및 분석** | **Google Gemini Embedding** | `text-embedding-004` 모델을 활용하여 768차원 고차원 의미 벡터 생성 |
| **AI 및 생성** | **Google Gemini Generative** | `gemini-2.0-flash` 모델 탑재 및 실시간 RAG 기반 답변 생성 |
| **장애 복원력** | **3단계 강건성 복원력 엔진** | 1차 Vertex AI SDK 호출 -> 실패 시 2차 Generative Language HTTP REST API 폴백 -> 최종 API 마비 시 3차 Local Offline Heuristic 엔진으로의 3중 폴백 보장 |
| **텍스트 인텔리전스** | **ABSA 분석 엔진** | 속성 기반 감성 분석(Aspect-Based Sentiment Analysis) 엔진 탑재로 성분/피부, 제형/발림성, 용기/디자인 스코어링 강제 |
| **통계 복원력** | **Heuristic 점수 복원 엔진** | 통계 집계 시 감성 스코어 컬럼이 누락된 구형 레코드 대상 정규식 역추출 및 평점/키워드 가중치 기반 휴리스틱 추정으로 통계 왜곡 방지 |
| **데이터 파이프라인** | **Selenium 4.0.0+ & curl_cffi 0.6.0+** | Edge 모바일 에뮬레이션 및 가상 스크롤, XHR/Fetch API 인터셉터를 통한 올리브영 데이터 수집 (도커 배포 종속성에서 제외하여 프로덕션 경량화 달성) |
| | **Pandas 2.0.0+ & openpyxl 3.1.0+** | 평점 균등 샘플링 가공 후 프리미엄 엑셀 적재 지원 (로컬 전용 패키지 격리) |
| **보안 및 미들웨어** | **pyjwt 2.8.0+** | C/Rust 컴파일러 빌드 오류 방지를 위해 `python-jose`를 대체한 순수 파이썬(Pure Python) JWT 기반 인증 아키텍처 구현 |
| | **hashlib & hmac** | C/Rust 의존성이 무거운 `bcrypt`를 우회하여 순수 파이썬 해시 솔팅 및 단방향 암호화 처리 구현 |
| | **Pydantic v2** | 컴파일 레벨 데이터 유효성 검증 및 인젝션 공격 원천 차단 |
| **테스트 및 APM** | **Pytest 8.0.0+** | 단위/통합 테스트 자동화 스위트 구축 |
| | **HTTPX Client** | API 통합 테스트용 비동기 비차단 HTTP 통신 지원 |
| | **Sentry SDK 1.40.0+** | 실시간 APM 모니터링, 예외 트래킹 및 성능 매트릭스 수집 |

---

## 🏗️ 주요 아키텍처 결정 사항 (Architectural Decisions)

### 1. FastAPI + Uvicorn 비동기 아키텍처 및 Pydantic v2 정적 검증
- **비동기 동시성 제어**: 비동기 ASGI 웹 서버인 Uvicorig 위에서 FastAPI의 `async/await` 동시성 제어를 100% 활용하여 스루풋(Throughput)을 극대화하고 최저 대기시간(Latency)을 보장합니다.
- **스키마 수준 검증**: Pydantic v2 기반의 엄격한 데이터 유효성 검증 레이어를 구축하여 API 엔드포인트 도달 전에 비정상적인 데이터 주입을 원천 차단하고 구조화된 데이터 흐름(DTO 패턴)을 강제합니다.

### 2. pgvector 기반 실시간 시맨틱 검색 통합 (pgvector Semantic Search) [UPDATE]
- **pgvector 통합 아키텍처**: 기존의 외부 Pinecone 벡터 데이터베이스 의존성을 완전히 걷어내고, **GCP Cloud SQL PostgreSQL의 pgvector 확장 기능**을 전면에 도입했습니다.
- **768차원 임베딩 결합**: `text-embedding-004` 모델을 통해 생성된 768차원 의미 벡터를 RDBMS의 `embedding` 컬럼(vector 타입)에 직접 결합하여 단일 데이터베이스 내에서 코사인 유사도 검색(`embedding <=> %s::vector ASC`)을 비동기로 완벽히 처리합니다.

### 3. RAG(Retrieval-Augmented Generation) 및 Gemini 멀티 모델 생성 엔진
- **동적 프레임워크 RAG**: 데이터베이스 검색 컨텍스트(Context)와 질문 프롬프트를 동적으로 조립하여 환각 현상(Hallucination)을 제어하는 RAG 아키텍처 기반 생성 엔진을 구축하였습니다.
- **Graceful Degradation (유연한 성능 저하)**: 최신 초고속 모델인 `gemini-2.0-flash`를 기본 엔진으로 설정하고, API 할당량 초과(Quota Limit) 또는 장애 발생 시 `gemini-1.5-flash` 모델로 자동 하향 다운그레이드 처리하여 사용자 서비스 마비를 방지합니다.

### 4. 속성 기반 감성 분석(ABSA) 및 다차원 평점 분석 엔진
- **텍스트 인텔리전스 고도화**: 단순한 긍정/부정 판단을 넘어 수집된 리뷰 텍스트를 정밀하게 분석하기 위해 속성 기반 감성 분석(ABSA) 엔진을 탑재하였습니다.
- **다차원 감성 분류**: 리뷰 본문으로부터 화장품의 핵심 속성(성분/피부 고민 점수, 제형/발림성 점수, 용기/디자인 점수)을 0.0 ~ 1.0 점수 스케일로 추출하고, 구체적인 불만 유형(자극, 제형불만 등)을 분류하여 실시간으로 대시보드 데이터로 매핑합니다.

### 5. 단일 RDBMS 트랜잭션 원자성 및 자가 치유 엔진 (Atomic Transaction & Self-Healing) [UPDATE]
- **단일 트랜잭션 원자성**: 기존 Supabase와 Pinecone 간의 분산 데이터베이스 정합성을 지키기 위해 수행되던 복잡한 이종 트랜잭션 롤백 로직을 폐기했습니다. pgvector 통합에 따라 **표준 RDBMS의 `rollback()` 처리 단 한 줄**로 원데이터와 벡터 인덱스의 완벽한 원자적 트랜잭션 성공을 보장합니다.
- **자가 치유 (Self-Healing) 파이프라인**: 대량의 데이터 적재 중 데이터베이스의 스키마 미매치나 특정 비정상 컬럼 에러 발생 시, 시스템이 중단되지 않고 해당 점수 데이터를 요약 텍스트로 보완 적재하는 자가 치유 파이프라인을 세밀히 설계했습니다.

### 6. 3단계 가용성 폴백 및 Heuristic 점수 복원력 (3-Tier Fallback & Heuristic Scorer) [UPDATE]
- **3중 복원 가용성 구조**: Vertex AI SDK 연결 장애 또는 외부 API 할당량 소진 시 1) Generative REST API로의 HTTP 폴백을 수행하고, 인터넷 전체 차단 시 2) 로컬 룰 베이스 및 더미 인사이트 요약기(Korean Rule-based Engine)로 무중단 폴백합니다.
- **Heuristic 점수 복원**: 리뷰 데이터 애그리게이션 시 개별 감성 점수 컬럼이 누락된 구형 레코드가 있을 경우, **정규식(Regular Expression)으로 `ai_summary` 내 점수를 역추출**하거나 이마저 실패 시 리뷰 평점 및 특정 뷰어 키워드(자극, 진정, 끈적임 등)를 바탕으로 감성 점수를 정교히 추론하는 Heuristic 점수 복원 엔진을 탑재하여 통계 왜곡을 원천 차단합니다.

### 7. 모바일 웹 시뮬레이션 및 API 인터셉터 기반 데이터 수집 파이프라인
- **Shadow DOM 렌더링 극복**: 올리브영 모바일 웹의 가상 스크롤(Virtual Scroll) 및 Shadow DOM 렌더링 한계를 우회하고자 Edge 모바일 에뮬레이션 및 가상 스크롤 트리거 브라우저 환경을 설계하였습니다.
- **XHR/Fetch API 인터셉터**: 브라우저 네트워크단에서 `/review/api/v2/reviews/cursor` API의 원시 통신 응답을 실시간으로 가로채는 인터셉터 기술을 적용해 오차 없는 원문 데이터를 정밀 획득합니다.
- **벌크 Upsert**: 수집된 데이터는 평점별 균등 샘플링과 해시 기반의 UUID5 생성 파이프라인을 통과하여, 중복을 원천 배제한 상태로 데이터베이스에 bulk upsert 처리됩니다.

### 8. 경량화 프로덕션 빌드 및 무제한 이식성 (Lightweight Container & Zero-Compile Errors) [NEW]
- **배포 빌드 안정성 극대화**: 컨테이너 빌드 및 서버리스 배포 환경에서 C/Rust 컴파일러 부재나 OpenSSL 라이브러리 충돌로 빌드가 실패하는 문제를 예방하고자 프로덕션 의존성(`requirements.txt`)을 극도로 경량화했습니다.
  - `google-cloud-sql-connector` 대신 `pg8000` 직접 UNIX 소켓 연결 탑재.
  - `google-cloud-aiplatform` Vertex SDK 대신 HTTP REST API 통신 유연화.
  - `python-jose`, `bcrypt` 등 컴파일 무거운 보안 팩을 순수 파이썬 구현체 `pyjwt`로 대체.
  - 로컬 전용 크롤러 라이브러리(`selenium`, `pandas`, `curl_cffi` 등)를 도커 배포 목록에서 제외하여 컨테이너 경량화 및 빌드 성공률 100% 달성.

---

## 📂 Domain 기반 폴더 구조 (Domain-based MVC + Repository Architecture) [UPDATE]

프로젝트는 **Domain 기반 MVC + Repository 아키텍처**로 구성되어 있다. 각 도메인이 `router / service / repository / schemas` 4개 레이어를 완전히 캡슐화하며, 도메인 간 경계가 명확히 분리된다.

```text
TONES_Server/
├── app/                            # FastAPI 서버 핵심 애플리케이션 소스 코드
│   │
│   ├── domains/                    # 도메인 단위 레이어 캡슐화 (MVC + Repository)
│   │   ├── router.py               # 전체 도메인 라우터 통합점 (마스터 라우터)
│   │   ├── auth/                   # 인증 도메인
│   │   │   ├── router.py           # Controller — HTTP 요청/응답, JWT 발급 라우팅
│   │   │   ├── service.py          # Service — 인증 비즈니스 로직 (로그인 검증, 비밀번호 재설정 등)
│   │   │   └── schemas.py          # DTO — Token, UserLogin, FindEmail/Password 스키마
│   │   ├── users/                  # 사용자 도메인
│   │   │   ├── router.py           # Controller — 사용자 프로필 조회 라우팅
│   │   │   ├── service.py          # Service — 사용자 CRUD 비즈니스 로직
│   │   │   ├── repository.py       # Repository — users 테이블 전담 DB 쿼리 (auth/admin 도메인 공유)
│   │   │   └── schemas.py          # DTO — User, UserCreate, UserUpdate 스키마
│   │   ├── products/               # 제품 도메인
│   │   │   ├── router.py           # Controller — 제품 목록/등록/수정/동기화 라우팅
│   │   │   ├── service.py          # Service — 제품 관리 비즈니스 로직
│   │   │   ├── repository.py       # Repository — products 테이블 전담 DB 쿼리
│   │   │   └── schemas.py          # DTO — ProductSchema, ProductCreatePayload 스키마
│   │   ├── reviews/                # 리뷰 도메인
│   │   │   ├── router.py           # Controller — 리뷰 조회/내보내기/벌크 적재 라우팅
│   │   │   ├── service.py          # Service — 리뷰 필터링, AI ABSA 파이프라인 적재 로직
│   │   │   ├── repository.py       # Repository — reviews 테이블 전담 DB 쿼리 (pgvector 포함)
│   │   │   └── schemas.py          # DTO — ReviewSchema, ReviewCreate 스키마
│   │   ├── dashboard/              # 대시보드 도메인
│   │   │   ├── router.py           # Controller — 대시보드 통계/AI 브리핑/보고서 라우팅
│   │   │   ├── service.py          # Service — WoW 통계 집계, 인사이트, TTL 캐싱, 보고서 생성 로직
│   │   │   ├── repository.py       # Repository — 대시보드 통계 전담 DB 쿼리
│   │   │   └── schemas.py          # DTO — DocsExportRequest/Response 스키마
│   │   ├── ai_search/              # AI 검색 도메인
│   │   │   ├── router.py           # Controller — 시맨틱 검색/RAG 생성/챗봇 라우팅
│   │   │   ├── service.py          # Service — Gemini 임베딩/생성, ABSA, 트렌드 브리핑, 3단계 폴백 로직
│   │   │   ├── repository.py       # Repository — pgvector 코사인 유사도 검색 전담 DB 쿼리
│   │   │   └── schemas.py          # DTO — SearchRequest/Response, GenerateRequest/Response, AIChatRequest/Response
│   │   ├── layout/                 # 레이아웃 도메인
│   │   │   ├── router.py           # Controller — 위젯 고정 레이아웃 조회/저장 라우팅
│   │   │   ├── service.py          # Service — 레이아웃 저장/로드 로직
│   │   │   ├── repository.py       # Repository — user_layouts 테이블 전담 DB 쿼리
│   │   │   └── schemas.py          # DTO — LayoutSaveRequest, LayoutResponse 스키마
│   │   ├── settings/               # 설정 도메인
│   │   │   ├── router.py           # Controller — 시스템 설정 조회/수정/초기화 라우팅
│   │   │   ├── service.py          # Service — 설정 관리 비즈니스 로직
│   │   │   ├── repository.py       # Repository — settings 테이블 전담 DB 쿼리
│   │   │   └── schemas.py          # DTO — SettingsUpdatePayload 스키마
│   │   ├── admin/                  # 관리자 도메인
│   │   │   ├── router.py           # Controller — 관리자 계정 CRUD 라우팅
│   │   │   ├── service.py          # Service — 관리자 계정 관리 로직 (UserRepository 위임)
│   │   │   └── schemas.py          # DTO — AdminUserCreatePayload, AdminUserUpdatePayload 스키마
│   │   └── integrations/           # 외부 연동 도메인
│   │       ├── router.py           # Controller — 연동 상태 조회 라우팅
│   │       ├── service.py          # Service — 연동 상태 서비스 로직
│   │       └── repository.py       # Repository — integrations 테이블 전담 DB 쿼리
│   │
│   ├── database/                   # 데이터베이스 인프라 레이어
│   │   ├── connection.py           # GCP Cloud SQL 연결 관리 (UNIX 소켓 / TCP/IP 이중 폴백)
│   │   ├── mock_data.py            # 오프라인 목업 데이터 (도메인 간 공유 폴백 데이터)
│   │   ├── gcp_schema.sql          # GCP Cloud SQL PostgreSQL + pgvector 운영계 데이터베이스 스키마
│   │   └── new_schema.md           # 신규 데이터베이스 스키마 설계 및 테이블 관계 문서
│   │
│   ├── core/                       # 프로젝트 전역 구성 및 보안 설정
│   │   ├── cache.py                # 인메모리 TTL 캐시 (TTLCache) 구현 및 싱글톤 캐시 제공
│   │   ├── config.py               # pydantic-settings 기반 환경변수 (.env) 검증 및 전역 구성 객체
│   │   ├── dependencies.py         # 공통 의존성 주입 (서비스 인스턴스 팩토리 및 현재 사용자 반환)
│   │   └── security.py             # 패스워드 솔팅 해싱 및 PyJWT 암호화/인증 핵심 보안 유틸리티
│   │
│   ├── crawler/                    # 데이터 수집 및 적재 파이프라인 (Local Execution Only)
│   │   ├── dump_shadow_dom.py      # 올리브영 웹페이지 Shadow DOM 트리 구조 디버깅 및 덤프 스크립트
│   │   ├── olive_young_crawler.py  # Selenium Edge 모바일 에뮬레이션 및 API 인터셉터 기반 올리브영 리뷰 수집 크롤러
│   │   └── upload_to_supabase.py   # 크롤링된 XLSX 데이터 분석 및 deterministic UUID5 생성을 거친 Cloud SQL 벌크 적재 엔진
│   │
│   └── main.py                     # FastAPI 인스턴스 생성, CORS/Sentry 미들웨어 초기 설정 (진입점)
│
├── tests/                          # Pytest 기반의 자동화 테스트 스위트 폴더
│   ├── conftest.py                 # FastAPI TestClient 모듈 수준 피스처(Fixture) 설정
│   ├── test_ai.py                  # AI 검색, RAG 답변 엔드포인트 및 AIService의 오프라인 폴백 동작 검증
│   ├── test_auth.py                # 가상 사용자 회원가입 및 JWT 액세스 토큰 발행 비즈니스 로직 단위 테스트
│   └── test_dashboard.py           # 대시보드 통계 조회 및 레이아웃 제어 API 엔드포인트 통합 테스트
│
├── .dockerignore                   # Docker 빌드 시 컨테이너에 제외할 파일/폴더 지정 목록
├── .env                            # [SECRET] 데이터베이스 소켓 경로, API 키 등의 런타임 환경변수
├── .env.example                    # 프로젝트 초기 세팅을 위한 환경변수 템플릿 파일
├── .gitignore                      # Git 버전 관리에서 제외할 바이너리 및 비밀 정보 목록
├── Dockerfile                      # 경량 멀티 스테이지 빌드 기반의 프로덕션 컨테이너 배포 구성 명세
├── cloudbuild.yaml                 # GCP Cloud Build 자동 빌드/배포 트리거 파이프라인 설정
├── deploy.sh                       # GCP Cloud Run 컨테이너 빌드 및 무중단 배포 자동화 셸 스크립트
├── requirements.txt                # 프로덕션 서버 빌드용 파이썬 패키지 최소 의존성 정의 (크롤러 패키지 제외로 빌드 극대화)
└── README.md                       # 프로젝트 소개 및 로컬 서버 구축 가이드 문서
```


---

> [!NOTE]
> 본 설계 문서는 Google AI Agent Challenge 프로젝트의 백엔드 아키텍처 및 핵심 엔지니어링 의사결정을 정의한 공식 안내서입니다. 신규 API 개발, 서비스 인스턴스 추가 및 외부 데이터베이스 파이프라인 수정 시 상기 기재된 3단계 가용성 보장 및 보안 정책 설계 원칙을 성실히 이행해 주시기 바랍니다.
