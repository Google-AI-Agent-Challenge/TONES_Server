# TONES Server — 백엔드 리팩토링 계획서

- **작성일**: 2026-06-04
- **대상 프로젝트**: TONES_Server
- **목표**: Domain 기반 MVC + Repository 아키텍처로 전환 (기능 변경 없음)

---

## 1. 배경 및 목적

현재 구조는 기능별 평면 분리(endpoints / services / schemas) 방식으로, 프로젝트 규모가 커질수록 다음 문제가 발생한다.

- Service 레이어에 DB 쿼리와 비즈니스 로직이 혼재
- 도메인 간 경계가 불명확하여 유지보수 난이도 증가
- 새 기능 추가 시 여러 디렉토리를 동시에 수정해야 하는 구조

이를 해결하기 위해 **도메인 단위로 관련 레이어를 묶는** 구조로 전환한다.

---

## 2. 아키텍처 비교

### 현재 구조

```
app/
├── api/
│   ├── deps.py
│   └── v1/
│       ├── api.py
│       └── endpoints/
│           ├── auth.py
│           ├── users.py
│           ├── ai_search.py
│           ├── dashboard.py
│           ├── reviews.py
│           ├── products.py
│           ├── layout.py
│           ├── admin.py
│           ├── settings.py
│           └── integrations.py
├── services/
│   ├── ai_service.py
│   ├── dashboard_service.py
│   ├── user_service.py
│   └── docs_service.py
├── schemas/
│   ├── auth.py
│   ├── user.py
│   ├── dashboard.py
│   └── ai_search.py
├── models/
│   ├── gcp_schema.sql
│   └── new_schema.md
└── core/
    ├── config.py
    ├── security.py
    └── cache.py
```

### 목표 구조

```
app/
├── domains/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── router.py       ← Controller (HTTP 요청/응답)
│   │   ├── service.py      ← Service (비즈니스 로직)
│   │   ├── repository.py   ← Repository (DB 쿼리 전담)
│   │   └── schemas.py      ← DTO (Pydantic 입출력)
│   ├── users/
│   ├── ai_search/
│   ├── dashboard/
│   ├── reviews/
│   ├── products/
│   ├── layout/
│   ├── admin/
│   ├── settings/
│   └── integrations/
├── database/
│   └── connection.py       ← DB 연결 로직 (deps.py에서 분리)
├── core/
│   ├── config.py           ← 변경 없음
│   ├── security.py         ← 변경 없음
│   ├── cache.py            ← 변경 없음
│   └── dependencies.py     ← 의존성 주입 (deps.py 이전)
└── main.py                 ← 변경 최소화
```

---

## 3. 레이어 역할 정의

| 레이어 | 파일 | 책임 |
|---|---|---|
| **Controller** | `router.py` | HTTP 요청/응답, 라우팅, 의존성 주입 수신 |
| **Service** | `service.py` | 비즈니스 로직, 외부 API 호출 (Gemini, Pinecone 등) |
| **Repository** | `repository.py` | PostgreSQL 쿼리 전담 — Service에서 완전히 분리 |
| **Schema** | `schemas.py` | Pydantic 입출력 DTO |

> **핵심 원칙**: Repository는 오직 DB I/O만 담당한다. 외부 API(Gemini, Pinecone, Google Docs)는 Service에 잔류한다.

---

## 4. 파일 이동 매핑

| 현재 경로 | 이전 후 경로 | 비고 |
|---|---|---|
| `app/api/deps.py` | `app/core/dependencies.py` | DB 연결은 database/connection.py로 추가 분리 |
| `app/api/v1/api.py` | `app/domains/router.py` | 도메인 라우터 통합점 |
| `app/api/v1/endpoints/auth.py` | `app/domains/auth/router.py` | |
| `app/api/v1/endpoints/users.py` | `app/domains/users/router.py` | |
| `app/api/v1/endpoints/ai_search.py` | `app/domains/ai_search/router.py` | |
| `app/api/v1/endpoints/dashboard.py` | `app/domains/dashboard/router.py` | |
| `app/api/v1/endpoints/reviews.py` | `app/domains/reviews/router.py` | |
| `app/api/v1/endpoints/products.py` | `app/domains/products/router.py` | |
| `app/api/v1/endpoints/layout.py` | `app/domains/layout/router.py` | |
| `app/api/v1/endpoints/admin.py` | `app/domains/admin/router.py` | |
| `app/api/v1/endpoints/settings.py` | `app/domains/settings/router.py` | |
| `app/api/v1/endpoints/integrations.py` | `app/domains/integrations/router.py` | |
| `app/services/user_service.py` | `app/domains/users/service.py` + `app/domains/auth/service.py` | 도메인 기준으로 분리 |
| `app/services/dashboard_service.py` | `app/domains/dashboard/service.py` | |
| `app/services/ai_service.py` | `app/domains/ai_search/service.py` | |
| `app/services/docs_service.py` | `app/domains/dashboard/service.py` (통합) | export 기능이 dashboard에 귀속 |
| `app/schemas/auth.py` | `app/domains/auth/schemas.py` | |
| `app/schemas/user.py` | `app/domains/users/schemas.py` | |
| `app/schemas/dashboard.py` | `app/domains/dashboard/schemas.py` | |
| `app/schemas/ai_search.py` | `app/domains/ai_search/schemas.py` | |
| *(신규)* | `app/domains/*/repository.py` (10개) | Service에서 DB 쿼리 추출 |
| *(신규)* | `app/database/connection.py` | |

---

## 5. 단계별 실행 계획

### Phase 1 — 공통 인프라 이전
**목표**: 도메인 작업 전 공통 레이어 정리

- [ ] `app/database/connection.py` 생성 — DB 연결 로직 이전
- [ ] `app/core/dependencies.py` 생성 — `deps.py`에서 서비스 주입 로직 이전
- [ ] `app/domains/router.py` 생성 — `api/v1/api.py` 라우터 통합 파일 이전
- [ ] `app/main.py` import 경로 업데이트

### Phase 2 — 도메인별 마이그레이션

도메인 간 의존성 순서를 고려한 작업 순서:

```
1. auth        (의존성 없음)
2. users       (auth 의존)
3. products    (독립적)
4. reviews     (products 의존)
5. dashboard   (reviews, products 의존)
6. ai_search   (reviews 의존)
7. layout      (독립적)
8. settings    (users 의존)
9. admin       (users 의존)
10. integrations (독립적)
```

각 도메인별 반복 작업:
1. `domains/{domain}/` 디렉토리 생성
2. `router.py` 작성 (기존 endpoint 이전)
3. `schemas.py` 작성 (기존 schema 이전)
4. `service.py` 작성 (기존 service에서 비즈니스 로직만 추출)
5. `repository.py` 작성 (service에서 DB 쿼리 분리 — **신규 레이어**)
6. `__init__.py` 작성

### Phase 3 — 테스트 및 정리

- [ ] `tests/` 내 import 경로 전체 업데이트
- [ ] `pytest` 전체 실행 — 기존 테스트 100% 통과 확인
- [ ] 구 디렉토리 삭제: `app/api/`, `app/services/`, `app/schemas/`
- [ ] 테스팅 보고서 작성

---

## 6. 진행 체크리스트

### Phase 1
- [ ] `database/connection.py`
- [ ] `core/dependencies.py`
- [ ] `domains/router.py`
- [ ] `main.py` 경로 업데이트

### Phase 2
- [ ] `domains/auth/`
- [ ] `domains/users/`
- [ ] `domains/products/`
- [ ] `domains/reviews/`
- [ ] `domains/dashboard/`
- [ ] `domains/ai_search/`
- [ ] `domains/layout/`
- [ ] `domains/settings/`
- [ ] `domains/admin/`
- [ ] `domains/integrations/`

### Phase 3
- [ ] 테스트 import 경로 업데이트
- [ ] pytest 전체 통과
- [ ] 구 디렉토리 삭제
- [ ] 테스팅 보고서 작성

---

## 7. 주의사항

1. **기능 변경 없음** — 모든 API 엔드포인트 경로(`/api/...`)와 응답 스키마는 그대로 유지
2. **ORM 미도입** — Raw pg8000 유지. Repository는 SQL 쿼리를 직접 보유
3. **병행 유지 원칙** — 각 도메인 완료 후 즉시 서버 기동 가능한 상태 유지 (절반 마이그레이션 중에도 서버 불중단)
4. **`review_crawler/` 변경 없음** — 도메인 구조 외부의 독립 유틸리티
5. **`app/models/` 처리** — SQL 파일만 존재하므로 `app/database/` 하위로 이동

---

## 8. 세션 분리 권장안 (토큰 관리)

작업량이 크므로 Phase별로 세션을 나눠 진행하는 것을 권장한다.

| 세션 | 작업 범위 |
|---|---|
| 세션 1 | Phase 1 전체 |
| 세션 2 | Phase 2 — auth, users, products |
| 세션 3 | Phase 2 — reviews, dashboard, ai_search |
| 세션 4 | Phase 2 — layout, settings, admin, integrations |
| 세션 5 | Phase 3 전체 |

각 세션 시작 시 이 문서의 체크리스트를 기준으로 현재 진행 상황을 확인한 후 작업을 이어간다.
