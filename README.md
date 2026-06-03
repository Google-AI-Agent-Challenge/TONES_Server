# 💄 TONES Server

> **우연최연우** 팀의 H&B 입점 뷰티 브랜드를 위한 AI 대화형 리뷰 관제 솔루션 — 백엔드 서버

---

## 🔗 배포 링크

| 구분 | URL |
| :--- | :--- |
| **백엔드 (API)** | https://tones-server-257637179317.us-central1.run.app |
| **프론트엔드** | https://tones-frontend-257637179317.us-central1.run.app |
| **API 문서 (Swagger)** | https://tones-server-257637179317.us-central1.run.app/docs |

---

## 📖 프로젝트 소개

하루 수만 건씩 쌓이는 고객 리뷰,<br>
아직도 실무자가 직접 읽고 계신가요?
<br>

**TONES**는 H&B 스토어 입점 뷰티 브랜드사를 위한<br>
B2B 특화 AI 리뷰 감성 분석 대시보드입니다.<br>
<br>
리뷰 원문·별점·제품 정보를 기반으로 고객 VOC를 분석하고,<br>
감성 분류·핵심 키워드·이슈 유형·변동 추이를 한 화면에서 시각화합니다.<br>
<br>
단순 키워드 검색이 아닌,<br>
"수분감은 좋지만 트러블이 발생했다"와 같은 양가감정 리뷰까지 분석할 수 있도록<br>
화장품 도메인 특화 ABSA(속성 기반 감성 분석) 구조를 적용했습니다.

---

## 🛠️ 기술 스택

| 구분 | 기술 |
| :--- | :--- |
| **프레임워크** | FastAPI 0.110.0+, Uvicorn 0.28.0+ |
| **언어** | Python 3.11+ (Type Hints) |
| **데이터베이스** | GCP Cloud SQL (PostgreSQL + pgvector 확장) |
| **DB 드라이버** | pg8000 — 순수 파이썬, C 컴파일러 불필요 |
| **AI / 임베딩** | Google Gemini `text-embedding-004` (768차원), Vertex AI SDK |
| **AI / 생성** | Google Gemini `gemini-2.0-flash` (RAG 답변·ABSA·브리핑) |
| **인증** | PyJWT 2.8.0+ (순수 파이썬 JWT, 컴파일 에러 없음) |
| **데이터 검증** | Pydantic v2 / Pydantic Settings v2 |
| **테스트** | Pytest 8.0.0+, HTTPX |
| **모니터링** | Sentry SDK 1.40.0+ |
| **배포** | Docker (멀티 스테이지 빌드), GCP Cloud Run, GCP Cloud Build |

---

## 🏗️ 아키텍처

### Domain 기반 MVC + Repository 구조

각 도메인이 `router / service / repository / schemas` 4개 레이어를 완전히 캡슐화한다. DB 쿼리는 Repository 레이어에서만 수행하며, 외부 API 호출(Gemini, Vertex AI)은 Service 레이어에 위치한다.

```text
TONES_Server/
├── app/
│   ├── domains/                    # 10개 도메인 (MVC + Repository)
│   │   ├── router.py               # 전체 도메인 라우터 통합점
│   │   ├── auth/                   # router · service · schemas
│   │   ├── users/                  # router · service · repository · schemas
│   │   ├── products/               # router · service · repository · schemas
│   │   ├── reviews/                # router · service · repository · schemas
│   │   ├── dashboard/              # router · service · repository · schemas
│   │   ├── ai_search/              # router · service · repository · schemas
│   │   ├── layout/                 # router · service · repository · schemas
│   │   ├── settings/               # router · service · repository · schemas
│   │   ├── admin/                  # router · service · schemas
│   │   └── integrations/           # router · service · repository
│   ├── database/
│   │   ├── connection.py           # GCP Cloud SQL 연결 (UNIX 소켓 / TCP/IP 이중 폴백)
│   │   ├── mock_data.py            # 오프라인 폴백 목업 데이터
│   │   ├── gcp_schema.sql          # PostgreSQL + pgvector 스키마 DDL
│   │   └── new_schema.md           # 스키마 설계 문서
│   ├── core/
│   │   ├── config.py               # 환경변수 (.env) 검증 및 전역 설정 객체
│   │   ├── security.py             # 패스워드 해싱 및 JWT 유틸리티
│   │   ├── cache.py                # 인메모리 TTL 캐시
│   │   └── dependencies.py         # 서비스 의존성 주입 팩토리
│   ├── crawler/                    # 데이터 수집 파이프라인 (로컬 전용)
│   │   ├── olive_young_crawler.py
│   │   ├── dump_shadow_dom.py
│   │   └── upload_to_supabase.py
│   └── main.py                     # FastAPI 진입점
├── tests/
│   ├── conftest.py
│   ├── test_ai.py
│   ├── test_auth.py
│   └── test_dashboard.py
├── asset/                          # API 명세서, 기술 의사결정 문서
├── .env.example
├── Dockerfile
├── cloudbuild.yaml
├── deploy.sh
└── requirements.txt
```

### ⚙️ 시스템 아키텍처 다이어그램

<img src="./asset/시스템%20아키텍처.png" width="500"/>

---

## 🔑 핵심 설계 특징

### 1. 3단계 강건성 복원 엔진
Gemini API 장애·할당량 소진 시 자동으로 3단계 폴백:
1. **Vertex AI SDK** → 실패 시
2. **Generative Language HTTP REST API** → 실패 시
3. **로컬 룰 기반 Heuristic 엔진** (오프라인 완전 동작 보장)

### 2. pgvector 통합 시맨틱 검색
외부 Pinecone 벡터 DB 의존성을 제거하고 GCP Cloud SQL의 pgvector 확장으로 통합. RDBMS `rollback()` 한 줄로 임베딩 벡터와 리뷰 데이터의 원자적 트랜잭션을 보장한다.

### 3. 자가 치유(Self-Healing) 파이프라인
대량 리뷰 적재 중 스키마 미매치가 감지되면 시스템을 중단하지 않고, 스코어 데이터를 요약 텍스트로 보완 적재한 뒤 자동 복구한다.

### 4. 경량화 프로덕션 빌드
C/Rust 컴파일러가 없는 Cloud Run 환경에서도 100% 빌드 성공을 보장:
- `bcrypt` / `python-jose` → `pyjwt` (순수 파이썬) 대체
- `google-cloud-sql-connector` → `pg8000` 직접 UNIX 소켓 연결 대체
- 크롤러 라이브러리(`selenium`, `pandas` 등)는 Docker 빌드에서 제외

---

## 🚀 로컬 실행 방법

### 1. 저장소 클론

```shell
git clone https://github.com/Google-AI-Agent-Challenge/TONES_Server.git

cd TONES_Server
```

### 2. 환경변수 설정

- `.env.example`을 복사하여 `.env`를 생성하고 값을 채운다.

```shell
cp .env.example .env
```

```env
# App Config
PROJECT_NAME="TONES Server"
API_V1_STR="/api"
SECRET_KEY="your-secret-key"
ACCESS_TOKEN_EXPIRE_MINUTES=60

# GCP & Cloud SQL Config
GCP_PROJECT_ID="your-gcp-project-id"
GCP_REGION="us-central1"
CLOUD_SQL_CONNECTION_NAME="project:region:instance"
DB_USER="postgres"
DB_PASS="your-db-password"
DB_NAME="your-db-name"
DB_HOST="localhost"        # 로컬 개발 시 Cloud SQL Proxy 주소
DB_PORT=5432

# Sentry Config (선택)
SENTRY_DSN=""

# Google Gemini Config
GEMINI_API_KEY="your-gemini-api-key"

# Google Service Account (Google Docs 연동 시 필요)
GOOGLE_SERVICE_ACCOUNT_JSON=""
```

> DB 연결 없이도 오프라인 목업 데이터로 모든 API가 동작한다.

### 3. 가상환경 구성 및 패키지 설치

```shell
python -m venv .venv

source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install pytest httpx          # 테스트 실행 시 추가 설치
```

### 4. 서버 실행

```shell
uvicorn app.main:app --reload --port 8080
```

> 실행 후 http://localhost:8080/docs 에서 Swagger UI를 확인할 수 있다.

### 5. 테스트 실행

```shell
pytest tests/ -v
```

```
15 passed in 1.24s
```

---

## 🗄️ 데이터베이스 초기화

- GCP Cloud SQL에 접속하여 `app/database/gcp_schema.sql`에 위치한 SQL 파일의 쿼리를 실행한다.<br>
- 또는 로컬에서 아래의 명령어를 입력한다.

```shell
psql -h <DB_HOST> -U <DB_USER> -d <DB_NAME> -f app/database/gcp_schema.sql
```

---

## 🐳 Docker 빌드 및 배포

```shell
# 로컬 Docker 빌드
docker build -t tones-server .
docker run -p 8080:8080 --env-file .env tones-server

# GCP Cloud Run 배포 (deploy.sh 사용)
./deploy.sh
```

> GCP Cloud Build를 통한 자동 배포는 `cloudbuild.yaml` 설정을 따른다.

---

## 📋 API 요약

> 전체 API 명세는 [`asset/api-specification.md`](./asset/api-specification.md)를 참고한다.

| 도메인 | Base Path | 주요 기능 |
| :--- | :--- | :--- |
| Auth | `/api/auth` | 로그인, 회원가입, 토큰 발급 |
| Users | `/api/users` | 사용자 프로필 조회 |
| Dashboard | `/api/dashboard` | 통계 요약, 트렌드 분석, AI 브리핑 |
| Reviews | `/api/reviews` | 리뷰 조회, 필터링, CSV 내보내기, 대량 적재 |
| Products | `/api/products` | 제품 관리, 동기화 |
| AI | `/api/ai` | 시맨틱 검색, RAG 챗봇, 인사이트 브리핑 |
| Layout | `/api/layout` | 위젯 레이아웃 저장/조회 |
| Settings | `/api/settings` | 시스템 설정 관리 |
| Admin | `/api/admin` | 관리자 계정 CRUD |
| Integrations | `/api/integrations` | 외부 플랫폼 연동 상태 |
