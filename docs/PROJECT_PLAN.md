# UXFlow Agent 프로젝트 계획서

## 1. 프로젝트 한 줄 소개

UXFlow Agent는 서비스 아이디어를 입력하면, 여러 Agent가 협력하여 **프론트엔드 화면 구성·사용자 흐름·UI 컴포넌트·UX 품질**을 순서대로 검토하는 멀티 에이전트 서비스입니다.

## 2. 문제와 목표

### 해결하려는 문제

프론트엔드 개발을 시작할 때 “화면을 몇 개 만들어야 하는지”, “사용자가 어떤 순서로 이동하는지”, “어떤 컴포넌트를 재사용해야 하는지”를 정하지 않으면 구현이 늦어지고 화면 품질도 일정하지 않을 수 있습니다.

### 목표

- 서비스 요구사항을 화면 단위 계획으로 바꾼다.
- 사용자의 핵심 목표가 복잡하지 않도록 UX 기준으로 검수한다.
- 안전한 컴포넌트·아이콘 소스를 추천한다.
- 각 Agent의 입력과 출력을 계약으로 검증해 잘못된 결과가 다음 단계로 넘어가지 않게 한다.
- Swagger에서 전체 과정을 눈으로 확인할 수 있게 한다.

## 3. 대상 사용자

| 대상 | 필요한 도움 |
| --- | --- |
| 프론트엔드 입문자 | 만들 페이지 수와 화면별 역할을 먼저 정리 |
| 기획자·학습자 | 서비스 아이디어를 사용자 흐름으로 구체화 |
| 팀 프로젝트 구성원 | 공통 컴포넌트와 UX 기준을 같은 방식으로 합의 |

## 4. Agent 전체 흐름

```text
사용자 요구사항
   ↓
Planner Agent
   ↓  (페이지 수·화면·사용자 흐름 계약 검증)
Component Recommender Agent
   ↓  (페이지별 UI·아이콘 계약 검증)
UX Reviewer Agent
   ↓  (5점 UX 기준 검증)
Figma Builder Agent
   ↓
Final Reviewer Agent
   ↓
최종 결과와 Trace 반환
```

### Agent 역할

| Agent | 하는 일 | 다음 단계로 넘기는 결과 |
| --- | --- | --- |
| Planner | 요구사항을 페이지 목록, 화면 수, 사용자 흐름으로 변환 | `PagePlan` |
| Component Recommender | 페이지마다 필요한 UI·아이콘과 공통 컴포넌트 추천 | `ComponentRecommendation` |
| UX Reviewer | 명확한 행동, 오류 안내, 완료 피드백 등 6개 UX 항목 점검 | `UsabilityReview` |
| Figma Builder | 승인된 기획을 Figma 생성 단계에 전달할 준비 | `FigmaBuildResult` |
| Final Reviewer | 기획한 화면 수와 실제 생성 결과가 일치하는지 확인 | `FinalReview` |

계약 검증 또는 UX 검수에서 실패하면 이후 Agent를 실행하지 않고, 실패 이유를 `trace`에 남깁니다.

## 5. 핵심 사용자 흐름 예시

여행 예약 서비스의 예시는 다음과 같습니다.

```text
검색 화면 → 상세 보기 화면 → 예약 요청 화면 → 완료 화면
```

각 화면에는 목적, 사용자의 핵심 행동, 필수 UI 요소가 포함됩니다. 예를 들어 검색 화면은 검색창·필터·결과 카드가 필요하며, 여러 화면에서 사용하는 버튼·오류 안내는 공통 컴포넌트로 분리합니다.

## 6. API 구성

| Method | API | 설명 |
| --- | --- | --- |
| GET | `/api/health` | 서버 실행 상태 확인 |
| GET | `/api/figma/status` | Figma 토큰의 설정 여부만 확인 |
| GET | `/api/contracts` | Agent 간 Pydantic 계약 확인 |
| POST | `/api/designs/plan` | 화면 계획 생성 |
| POST | `/api/designs/recommend-components` | 컴포넌트·아이콘 추천 |
| POST | `/api/designs/review` | UX 기준 검수 |
| POST | `/api/designs/run` | 전체 Agent 흐름 실행 |
| GET | `/api/designs/{run_id}` | 실행 Trace와 결과 조회 |

## 7. 현재 구현 상태

### 완료

- FastAPI와 Swagger API 구성
- Pydantic 기반 입력·출력 계약 검증
- Planner, Component Recommender, UX Reviewer, Figma Builder, Final Reviewer 구조
- 정상 흐름과 실패 흐름의 Trace 저장·조회
- `plan_only` 안전 실행 모드
- Figma 토큰 설정 여부 확인 API
- 자동 테스트 53개

### 아직 구현하지 않은 범위

- Figma 파일에 실제 프레임과 컴포넌트를 자동 생성하는 연결
- 사용자 로그인과 권한 관리
- 실행 결과의 데이터베이스 영구 저장
- React/HTML/CSS 프론트엔드 코드 자동 생성
- 서비스 배포 자동화

> Figma Personal Access Token은 현재 “토큰이 설정되어 있는지”만 확인합니다. Figma REST API만으로 화면을 작성하는 기능은 제공되지 않으므로, 실제 생성 단계에는 Figma Plugin 또는 Figma MCP 연동을 별도로 설계해야 합니다.

## 8. 다음 개발 단계

| 우선순위 | 단계 | 완료 기준 |
| --- | --- | --- |
| 1 | Figma 생성 연결 | 사용자 승인 후 Figma 파일에 화면을 만들고 실제 URL을 반환 |
| 2 | 프론트엔드 코드 연결 | 승인된 화면 계획을 React 컴포넌트 구조로 변환 |
| 3 | 결과 영구 저장 | 서버 재시작 후에도 `run_id` 결과를 조회 |
| 4 | 사용자 화면 | 비개발자도 폼으로 요구사항을 입력하고 결과를 확인 |
| 5 | 배포·운영 | 환경 변수, 로그, CI 테스트를 포함한 배포 흐름 |

## 9. 제출 시 시연 순서

1. 서버를 8000 포트에서 실행한다.
2. Swagger `/docs`를 연다.
3. `GET /api/health`로 서버 상태를 보여 준다.
4. `POST /api/designs/plan`에 서비스 요구사항을 넣어 페이지 수와 흐름을 확인한다.
5. 추천·검수 API를 순서대로 실행한다.
6. `POST /api/designs/run?mode=plan_only`로 전체 흐름을 실행한다.
7. 응답의 `run_id`로 `GET /api/designs/{run_id}`를 호출해 Agent Trace를 보여 준다.
8. `python -m pytest -q` 실행 결과를 보여 준다.

## 10. 완료 기준

- 요구사항으로부터 페이지 수와 사용자 흐름을 반환한다.
- 잘못된 계약 데이터는 다음 Agent로 전달되지 않는다.
- UX 기준을 통과하지 못하면 Figma 단계가 건너뛰어진다.
- Swagger에서 각 API와 전체 흐름을 테스트할 수 있다.
- Figma 토큰을 코드·응답·GitHub에 노출하지 않는다.
- 자동 테스트가 통과한다.
