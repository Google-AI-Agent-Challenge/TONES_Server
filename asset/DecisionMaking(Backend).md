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
| **데이터 레이어** | **Supabase Client SDK 2.3.0+** | PostgreSQL RDBMS 연동, 트랜잭션 처리 및 안정적인 데이터 CRUD |
| | **Pinecone Client SDK 3.1.0+** | 고성능 벡터 데이터베이스 연동 및 대규모 의미론적 검색 수행 |
| **AI 및 분석** | **Google Gemini Embedding** | `text-embedding-004` 모델을 활용하여 768차원 고차원 의미 벡터 생성 |
| | **Google Gemini Generative** | `gemini-2.0-flash` 모델 탑재 및 실시간 RAG 기반 답변 생성 |
| | **3단계 강건성 복원력 엔진** | 1차 `gemini-2.0-flash` 장애 시 2차 `gemini-1.5-flash` 자동 하향 Degradation, 최종 마비 시 3차 Local Offline Dummy로의 3중 폴백 보장 |
| | **ABSA 분석 엔진** | 속성 기반 감성 분석(Aspect-Based Sentiment Analysis) 엔진 탑재로 성분/피부, 제형/발림성, 용기/디자인 스코어링 강제 |
| **데이터 파이프라인** | **Selenium 4.0.0+ & curl_cffi 0.6.0+** | Edge 모바일 에뮬레이션 및 가상 스크롤, XHR/Fetch API 인터셉터를 통한 올리브영 데이터 수집 |
| | **Pandas 2.0.0+ & openpyxl 3.1.0+** | 평점 균등 샘플링 가공 후 프리미엄 엑셀 적재 지원 |
| **보안 및 미들웨어** | **python-jose 3.3.0+** | JWT 기반 무상태(Stateless) 토큰 인증 시스템 구현 |
| | **passlib + bcrypt 4.0.1+** | 강력한 단방향 비밀번호 솔트 및 해시 암호화 적용 |
| | **Pydantic v2** | 컴파일 레벨 데이터 유효성 검증 및 인젝션 공격 원천 차단 |
| **테스트 및 APM** | **Pytest 8.0.0+** | 단위/통합 테스트 자동화 스위트 구축 |
| | **HTTPX Client** | API 통합 테스트용 비동기 비차단 HTTP 통신 지원 |
| | **Sentry SDK 1.40.0+** | 실시간 APM 모니터링, 예외 트래킹 및 성능 매트릭스 수집 |

---

## 🏗️ 주요 아키텍처 결정 사항 (Architectural Decisions)

### 1. FastAPI + Uvicorn 비동기 아키텍처 및 Pydantic v2 정적 검증
- **비동기 동시성 제어**: 비동기 ASGI 웹 서버인 Uvicorn 위에서 FastAPI의 `async/await` 동시성 제어를 100% 활용하여 스루풋(Throughput)을 극대화하고 최저 대기시간(Latency)을 보장합니다.
- **스키마 수준 검증**: Pydantic v2 기반의 엄격한 데이터 유효성 검증 레이어를 구축하여 API 엔드포인트 도달 전에 비정상적인 데이터 주입을 원천 차단하고 구조화된 데이터 흐름(DTO 패턴)을 강제합니다.

### 2. AI 기반 하이브리드 검색 및 강건한 폴백 아키텍처
- **768차원 임베딩**: Google Gemini `text-embedding-004` 모델을 활용하여 사용자의 자연어 질문을 768차원의 의미론적 벡터로 실시간 인코딩합니다.
- **고가용성 벡터 검색**: Pinecone 벡터 데이터베이스와의 연동을 통해 고성능 시맨틱(Semantic) 검색을 수행하되, 외부 API 장애 혹은 오프라인 테스트 환경을 고려하여 자체 "오프라인 폴백(Offline Fallback)" 메커니즘을 설계함으로써 무중단 서비스 연속성을 보장합니다.

### 3. RAG(Retrieval-Augmented Generation) 및 Gemini 멀티 모델 생성 엔진
- **동적 프레임워크 RAG**: 데이터베이스 검색 컨텍스트(Context)와 질문 프롬프트를 동적으로 조립하여 환각 현상(Hallucination)을 제어하는 RAG 아키텍처 기반 생성 엔진을 구축하였습니다.
- **Graceful Degradation (유연한 성능 저하)**: 최신 초고속 모델인 `gemini-2.0-flash`를 기본 엔진으로 설정하고, API 할당량 초과(Quota Limit) 또는 장애 발생 시 `gemini-1.5-flash` 모델로 자동 하향 다운그레이드 처리하여 사용자 서비스 마비를 방지합니다.

### 4. 속성 기반 감성 분석(ABSA) 및 다차원 평점 분석 엔진
- **텍스트 인텔리전스 고도화**: 단순한 긍정/부정 판단을 넘어 수집된 리뷰 텍스트를 정밀하게 분석하기 위해 속성 기반 감성 분석(ABSA) 엔진을 탑재하였습니다.
- **다차원 감성 분류**: 리뷰 본문으로부터 화장품의 핵심 속성(성분/피부 고민 점수, 제형/발림성 점수, 용기/디자인 점수)을 0.0 ~ 1.0 점수 스케일로 추출하고, 구체적인 불만 유형(자극, 제형불만 등)을 분류하여 실시간으로 대시보드 데이터로 매핑합니다.

### 5. 고신뢰성 데이터 동기화: 자가 치유(Self-Healing) 및 트랜잭션 롤백
- **자가 치유 (Self-Healing)**: 대량의 데이터 적재 중 데이터베이스의 스키마 미매치나 특정 비정상 컬럼 에러 발생 시, 해당 컬럼을 실시간으로 제외하고 적재를 재시도하는 동적 폴백 프로세스를 탑재하여 적재 프로세스가 전체 중단되는 현상을 방지합니다.
- **이종 데이터베이스 트랜잭션 롤백**: Supabase와 Pinecone 등 물리적으로 분리된 저장소에 적재할 때 데이터 정합성을 보호하기 위해, Supabase 적재 실패 시 이미 Pinecone에 입력된 벡터 인덱스를 실시간으로 함께 추적하여 삭제(Rollback)하는 정합성 보장 로직을 설계했습니다.

### 6. 3단계 가용성 폴백 아키텍처 (3-Tier Graceful Fallback)
- Google Gemini API 장애나 로컬 부하 상황에서도 서비스의 영속성을 보장하고자 다음과 같은 3중 복원 구조를 적용하였습니다.
  * **1차 핵심 엔진**: `gemini-2.0-flash` 모델 활용 생성.
  * **2차 안정성 엔진**: 1차 호출 장애 발생 시 `gemini-1.5-flash` 모델로 자동 하향 다운그레이드.
  * **3차 오프라인 엔진**: 외부 클라우드 API 통신이 전체 마비될 경우, 로컬 룰 베이스 더미 대답 생성기 및 로컬 시맨틱 더미 리뷰 리스트를 즉각 구성하여 무중단 클라이언트 통신을 보장.

### 7. 모바일 웹 시뮬레이션 및 API 인터셉터 기반 데이터 수집 파이프라인
- **Shadow DOM 렌더링 극복**: 올리브영 모바일 웹의 가상 스크롤(Virtual Scroll) 및 Shadow DOM 렌더링 한계를 우회하고자 Edge 모바일 에뮬레이션 및 가상 스크롤 트리거 브라우저 환경을 설계하였습니다.
- **XHR/Fetch API 인터셉터**: 브라우저 네트워크단에서 `/review/api/v2/reviews/cursor` API의 원시 통신 응답을 실시간으로 가로채는 인터셉터 기술을 적용해 오차 없는 원문 데이터를 정밀 획득합니다.
- **벌크 Upsert**: 수집된 데이터는 평점별 균등 샘플링과 해시 기반의 UUID5 생성 파이프라인을 통과하여, 중복을 원천 배제한 상태로 데이터베이스에 bulk upsert 처리됩니다.

### 8. JWT 무상태 인증 및 엔드투엔드 보안 미들웨어
- `python-jose`와 `bcrypt` 알고리즘을 활용하여 사용자 비밀번호를 안전하게 단방향 해싱하여 저장하고, JWT(JSON Web Token) 기반의 Stateless 인증 아키텍처를 구현하였습니다.
- FastAPI의 의존성 주입(`Dependency Injection`) 메커니즘을 `app/api/deps.py`에 적용하여, 모든 주요 AI 리액션 및 데이터 검색 서비스에 대해 인가된 토큰 소유자만 안전하게 자원을 소비할 수 있도록 보안 레이어를 설계했습니다.

---

## 📂 계층형 폴더 구조 (Layered Folder Architecture)

프로젝트는 모듈별 명확한 역할 분담과 유지보수성을 극대화하기 위해 다음과 같은 계층형 디렉터리 아키텍처로 구성되었습니다.

```text
TONES_Server/
├── app/                            # FastAPI 서버 핵심 애플리케이션 소스 코드
│   ├── api/                        # API 엔드포인트 라우터 및 의존성 주입 레이어
│   │   ├── v1/                     # API 버전 1.0 라우터 그룹
│   │   │   ├── endpoints/          # 세부 도메인별 API 라우터 실체
│   │   │   │   ├── ai_search.py    # Pinecone 시맨틱 검색 및 Gemini AI 답변 생성 (POST)
│   │   │   │   ├── auth.py         # 회원가입 및 JWT 액세스 토큰 발급/로그인 (POST)
│   │   │   │   ├── dashboard.py    # 제품 목록, 최신 리뷰, 키워드 검색 등 데이터 조회 (GET)
│   │   │   │   └── users.py        # 로그인된 사용자 정보 조회 프로필 엔드포인트 (GET)
│   │   │   └── api.py              # v1 도메인별 라우터들을 하나로 통합하는 마스터 라우터
│   │   └── deps.py                 # 공통 의존성 주입 (JWT 인증 세션 및 공통 서비스 인스턴스 반환)
│   │
│   ├── core/                       # 프로젝트 전역 구성 및 보안 설정
│   │   ├── config.py               # pydantic-settings 기반 환경변수 (.env) 검증 및 전역 구성 객체
│   │   └── security.py             # bcrypt 패스워드 해싱 및 JWT 암호화/인증 핵심 보안 유틸리티
│   │
│   ├── models/                     # 데이터베이스 스키마 및 마이그레이션 관리
│   │   └── schema.sql              # Supabase PostgreSQL 초기 테이블 구성 및 인덱스 배치 SQL
│   │
│   ├── schemas/                    # Pydantic 데이터 검증 레이어 (DTO 역할 수행)
│   │   ├── ai_search.py            # AI 검색 및 답변 생성에 사용되는 요청/응답 스키마 명세
│   │   ├── auth.py                 # 로그인 정보 및 토큰 결과 스키마 명세
│   │   ├── dashboard.py            # 제품 및 리뷰 데이터 파싱용 Pydantic 스키마 정의
│   │   └── user.py                 # 사용자 가입 및 프로필 반환 구조 정의
│   │
│   ├── services/                   # 비즈니스 로직 및 외부 연동 인터페이스 구현
│   │   ├── ai_service.py           # Gemini 임베딩/생성 API 연동, Pinecone 검색 및 폴백 복원력 탑재
│   │   ├── dashboard_service.py    # Supabase DB 쿼리를 직접 수행하여 대시보드 데이터 통계 집계
│   │   └── user_service.py         # 사용자 비밀번호 확인, 신규 등록 및 프로필 반환 등 계정 서비스
│   │
│   └── main.py                     # FastAPI 인스턴스 생성, CORS/Sentry 미들웨어 초기 설정 (진입점)
│
├── tests/                          # Pytest 기반의 자동화 테스트 스위트 폴더
│   ├── conftest.py                 # FastAPI TestClient 모듈 수준 피스처(Fixture) 설정
│   ├── test_ai.py                  # AI 검색, RAG 답변 엔드포인트 및 AIService의 오프라인 폴백 동작 검증
│   └── test_auth.py                # 가상 사용자 회원가입 및 JWT 액세스 토큰 발행 비즈니스 로직 단위 테스트
│
├── .env.example                    # 프로젝트 초기 세팅을 위한 환경변수 템플릿 파일
├── .gitignore                      # Git 버전 관리에서 제외할 바이너리 및 비밀 정보 목록
├── Dockerfile                      # 멀티 스테이지 빌드 기반의 경량화된 컨테이너 배포 구성 명세
├── README.md                       # 프로젝트 소개 및 로컬 서버 구축 가이드 문서
├── requirements.txt                # FastAPI, Supabase, Pinecone 등 파이썬 패키지 의존성 정의
│
# ─── 데이터 수집 및 데이터 적재 파이프라인 (Data Pipeline Layer) ───
├── olive_young_crawler.py          # Selenium Edge 모바일 에뮬레이션 및 API 인터셉터 기반 올리브영 리뷰 수집 크롤러
└── upload_to_supabase.py           # 크롤링된 XLSX 데이터 분석 및 deterministic UUID5 생성을 거친 Supabase 벌크 적재 엔진
```

---

> [!NOTE]
> 본 설계 문서는 Google AI Agent Challenge 프로젝트의 백엔드 아키텍처 및 핵심 엔지니어링 의사결정을 정의한 공식 안내서입니다. 신규 API 개발, 서비스 인스턴스 추가 및 외부 데이터베이스 파이프라인 수정 시 상기 기재된 3단계 가용성 보장 및 보안 정책 설계 원칙을 성실히 이행해 주시기 바랍니다.
