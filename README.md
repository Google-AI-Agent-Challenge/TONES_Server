# TONES

> **우연최연우** 팀과 함께하는 H&B 입점 뷰티 브랜드를 위한 AI 대화형 리뷰 관제 솔루션

## 배포 링크

> [👉 구경하러 가기~!](https://frontend-eight-orcin-70.vercel.app/)

## 프로젝트 소개

> 하루 수만 건씩 쏟아지는 고객 리뷰, 아직도 실무자가 수작업으로 읽고 계신가요? TONES는 대형 H&B 스토어 입점 브랜드사를 위한 B2B 특화 리뷰 감성 분석 대시보드입니다. Vertex AI 기반의 다중 속성 감성 분석(ABSA)과 Dialogflow 자연어 처리 기술을 결합하여, 실무자가 일상적인 대화(Query)만으로 원하는 제품의 리스크 추이를 즉각 시각화하고 엑셀 리포트로 추출할 수 있는 완벽한 관제 인프라를 제공합니다.

## TONES Server

본 백엔드 서버는 **FastAPI**를 핵심 프레임워크로 채택하여 높은 동시성과 빠른 응답 속도를 자랑하며, 다음과 같은 핵심 비즈니스 로직을 처리합니다.

- **실시간 AI RAG 검색**: Google Gemini (`text-embedding-004`)를 활용하여 사용자 질문을 768차원 벡터로 변환하고, Pinecone 벡터 DB에서 유사도 검색을 수행합니다. 이후 최신 `gemini-2.0-flash` 모델을 통해 맥락에 맞는 최적의 답변을 생성합니다. API 오류 혹은 트래픽 제한 시 `gemini-1.5-flash` 모델로 자동 전환(Graceful Fallback)하고, 오프라인 모드용 로컬 Fallback 엔진을 탑재하여 가용성을 극대화합니다.

- **대시보드 통계 및 제품/리뷰 관리**: Supabase(PostgreSQL RDBMS)와 연동하여 제품 목록, 최신 리뷰, 통계 정보를 안정적으로 데이터 CRUD 및 집계 처리합니다.

- **보안 및 인증**: bcrypt 패스워드 해싱 및 무상태(Stateless) JWT 기반 인증 아키텍처를 도입하여 안전한 API 접근 제어를 보장합니다.

## 기술 스택

### 1. Core Framework & Web
* **Python 3.11+**
* **FastAPI 0.110.0+**: 고성능 비동기 API 웹 프레임워크 설계
* **Uvicorn standard 0.28.0+**: 고성능 ASGI 웹 서버 구동
* **Pydantic v2 / Pydantic Settings v2**: 컴파일 수준의 데이터 스키마 유효성 검증 및 환경변수 주입

### 2. Database & Data Layer
* **Supabase Client SDK 2.3.0+**: PostgreSQL RDBMS 연동 및 트랜잭션 CRUD 처리
* **Pinecone Client SDK 3.1.0+**: 고성능 벡터 데이터베이스 연동 및 시맨틱 검색

### 3. AI & Analytics
* **Google Gemini Embedding API**: `text-embedding-004` (768차원 의미 벡터 생성)
* **Google Gemini Generative API**: `gemini-2.0-flash` (기본 RAG 답변 생성) / `gemini-1.5-flash` (장애 시 자동 폴백)

### 4. Security & Middleware
* **python-jose 3.3.0+**: JWT 기반 무상태 토큰 인증 시스템
* **passlib[bcrypt] & bcrypt 4.0.1+**: 패스워드 해시 암호화
* **Sentry SDK 1.40.0+**: 실시간 에러 트래킹 및 모니터링 연동

### 5. Test & Quality
* **Pytest 8.0.0+**: 단위 및 통합 테스트 자동화 스위트
* **HTTPX Client**: 비동기 비차단 API 통합 테스트 지원

## 시스템 아키텍쳐

### 디렉토리 구조 (Layered Folder Architecture)
```text
WooYeonChoiYeonWoo_Server/
├── app/                            # FastAPI 서버 핵심 애플리케이션 소스
│   ├── api/                        # API 엔드포인트 및 의존성 주입 레이어
│   │   ├── v1/                     # API 버전 1 라우터 그룹
│   │   │   ├── endpoints/          # 세부 도메인별 API 라우터 실체
│   │   │   │   ├── ai_search.py    # Pinecone 시맨틱 검색 및 Gemini AI 답변 생성 (POST)
│   │   │   │   ├── auth.py         # 회원가입 및 JWT 로그인/액세스 토큰 발급 (POST)
│   │   │   │   ├── dashboard.py    # 제품 목록, 최신 리뷰, 키워드 검색 등 데이터 조회 (GET)
│   │   │   │   └── users.py        # 로그인된 사용자 프로필 정보 조회 엔드포인트 (GET)
│   │   │   └── api.py              # v1 도메인별 라우터를 통합하는 마스터 라우터
│   │   └── deps.py                 # 공통 의존성 주입 (JWT 인증 세션 및 공통 서비스 인스턴스 반환)
│   ├── core/                       # 프로젝트 전역 구성 및 보안 설정
│   │   ├── config.py               # pydantic-settings 기반 환경변수 (.env) 검증 및 전역 객체
│   │   └── security.py             # bcrypt 패스워드 해싱 및 JWT 암호화/인증 핵심 보안 유틸리티
│   ├── models/                     # 데이터베이스 스키마 및 마이그레이션 관리
│   │   └── schema.sql              # Supabase PostgreSQL 초기 테이블 구성 및 인덱스 배치 SQL
│   ├── schemas/                    # Pydantic 데이터 검증 레이어 (DTO 역할 수행)
│   │   ├── ai_search.py            # AI 검색 및 답변 생성 요청/응답 스키마
│   │   ├── auth.py                 # 로그인 및 JWT 토큰 결과 스키마
│   │   ├── dashboard.py            # 제품 및 리뷰 데이터 파싱용 스키마
│   │   └── user.py                 # 사용자 가입 및 프로필 반환 스키마
│   ├── services/                   # 비즈니스 로직 및 외부 연동 인터페이스 구현
│   │   ├── ai_service.py           # Gemini 임베딩/생성 API 연동, Pinecone 검색 및 폴백 복원력 탑재
│   │   ├── dashboard_service.py    # Supabase DB 쿼리를 직접 수행하여 대시보드 데이터 통계 집계
│   │   └── user_service.py         # 사용자 비밀번호 확인, 신규 등록 및 프로필 반환 등 계정 서비스
│   └── main.py                     # FastAPI 인스턴스 생성, CORS/Sentry 미들웨어 초기 설정 (진입점)
├── supabase/                       # Supabase DB 설정
│   ├── products.sql                # 테이블 정의
│   └── seed.sql                    # 초기 시드 데이터 적재
├── tests/                          # Pytest 기반의 자동화 테스트 스위트 폴더
│   ├── conftest.py                 # FastAPI TestClient 피스처 설정
│   ├── test_ai.py                  # AI 검색, RAG 답변 및 AIService 폴백 동작 검증
│   └── test_auth.py                # 회원가입 및 JWT 토큰 발행 비즈니스 로직 단위 테스트
├── .env.example                    # 프로젝트 초기 세팅을 위한 환경변수 템플릿
├── Dockerfile                      # 멀티 스테이지 빌드 기반의 경량화된 컨테이너 배포 구성 명세
└── requirements.txt                # 파이썬 패키지 의존성 정의
```

### 💻 시스템 아키텍처 흐름 (Workflow)
<img src="./asset/시스템%20아키텍처.png" width="500" height="700"/>

## 사용 방법

### git clone 실행
```shell
$ git clone https://github.com/Google-AI-Agent-Challenge/TONES_Server.git
```

### 시스템 설정

#### 1. 환경 변수 파일(`.env`) 추가
- 루트 디렉토리에 `.env` 파일을 추가해주세요. (`.env.example` 파일을 복사하여 사용할 수 있습니다.)
- **Supabase**, **Pinecone**, **Google Gemini** 및 **Sentry** 연동 설정이 필요합니다.

```env
# App Config
PROJECT_NAME="WooYeonChoiYeonWoo Server"
API_V1_STR="/api/v1"
SECRET_KEY="your-super-secret-key-change-this-in-production"
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Supabase Config
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your-supabase-anon-key"
SUPABASE_SERVICE_ROLE_KEY="your-supabase-service-role-key"

# Pinecone Config
PINECONE_API_KEY="your-pinecone-api-key"
PINECONE_ENVIRONMENT="your-pinecone-environment"
PINECONE_INDEX_NAME="your-pinecone-index-name"

# Sentry Config
SENTRY_DSN=""

# Google Gemini Config
GEMINI_API_KEY="your-gemini-api-key"
```

#### 2. 패키지 설치 및 실행
- 가상환경을 구성하고 필요한 의존성을 설치한 뒤, 로컬 Uvicorn 서버를 실행합니다.

```shell
# 가상환경 생성 및 활성화
$ python -m venv .venv
$ source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 패키지 설치
$ pip install -r requirements.txt

# 로컬 개발 서버 실행
$ uvicorn app.main:app --reload
```

#### 3. Supabase 초기화 및 스키마 설정
- `supabase` 디렉토리에 작성된 SQL 스크립트를 사용하여 DB 테이블 및 기초 데이터를 적재합니다.
  - `supabase/products.sql` 파일을 실행하여 스키마를 구성합니다.
  - `supabase/seed.sql` 파일을 실행하여 테스트용 대량 리뷰/제품 시드 데이터를 로드합니다.

#### 4. 테스트 수행
- pytest를 통해 비즈니스 로직과 API 가동 상태를 자동으로 검증할 수 있습니다.
```shell
$ pytest
```
