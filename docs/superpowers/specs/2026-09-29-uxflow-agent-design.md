# UXFlow Agent Design Specification

## 1. 목적

UXFlow Agent는 사용자의 웹서비스 요구를 받아, 필요한 프론트엔드 페이지와 공통
컴포넌트를 설계하고, 사용성 기준을 통과한 설계만 Figma 화면 생성 단계로 전달하는
교육용 멀티 에이전트 서비스다. 사용자가 첫 화면부터 핵심 목표를 쉽게 완료하도록
돕는 것을 최우선 품질 기준으로 둔다.

## 2. 사용자와 성공 기준

### 대상 사용자

- 웹서비스 아이디어는 있지만 페이지 구성과 UX 설계가 익숙하지 않은 기획자·학습자
- Figma에 만들 화면의 범위와 순서를 먼저 정리하고 싶은 프론트엔드 개발자

### 성공 기준

- 사용자가 자연어 요구사항 한 번으로 페이지 목록, 페이지 수, 사용자 흐름을 받는다.
- 모든 페이지는 목적, 핵심 행동, 필수 UI 요소를 가진다.
- 공통 UI는 재사용 컴포넌트로 분리된다.
- 검수에 실패한 기획은 Figma 생성 단계로 전달하지 않는다.
- 검수 결과는 "만족도 5점 기준"에서 통과·보완 필요와 근거를 명확히 보여 준다.
- Figma 연동이 설정된 경우에만 승인된 설계를 Figma 파일에 쓴다. 연동 실패 시
  설계 결과와 실패 원인을 보존한다.

## 3. 범위

### 1차 버전에 포함

- 새 웹서비스 화면 기획
- 페이지 수와 페이지별 목적 산정
- 사용자 흐름과 공통 컴포넌트 제안
- UX 품질 검수
- 검수된 설계의 Figma 생성 요청 준비 및 실행
- FastAPI Swagger API를 통한 각 단계 테스트
- 요청·결과·검수 Trace 조회

### 1차 버전에서 제외

- 로그인, 결제, 실제 배포 자동화
- 기존 Figma 파일의 복잡한 대규모 편집
- 완성된 React/HTML/CSS 코드 자동 생성
- 브랜드 자산 또는 유료 이미지 자동 구매

## 4. 멀티 에이전트 구조

```text
사용자 요구사항
  → Planner Agent
  → Plan Contract Guard
  → UX Reviewer Agent
  → Review Contract Guard
  ├─ 보완 필요: 개선 요청과 함께 Planner Agent 종료
  └─ 통과: Figma Builder Agent
             → Figma Result Guard
             → Final Reviewer Agent
             → 최종 결과
```

### Planner Agent

책임:

- 서비스 목표와 사용자 목표를 한 문장으로 정리한다.
- 페이지 목록, 페이지 수, 페이지 간 사용자 흐름을 작성한다.
- 페이지별 핵심 행동과 필요한 UI 요소를 작성한다.
- 재사용 가능한 공통 컴포넌트를 분리한다.

하지 않는 일:

- Figma 파일을 직접 수정하지 않는다.
- UI 품질을 스스로 최종 승인하지 않는다.

### UX Reviewer Agent

책임:

- 페이지 누락·중복·불필요한 단계가 없는지 점검한다.
- 핵심 행동이 3회 이내 클릭으로 가능한지 평가한다.
- 안내 문구, 오류 안내, 모바일 고려, 접근성, 완료 피드백을 점검한다.
- 통과 또는 보완 필요를 근거와 함께 반환한다.

### Figma Builder Agent

책임:

- 통과한 페이지 설계와 디자인 토큰을 Figma 화면 명세로 변환한다.
- Figma 연결이 가능할 때만 새 파일 또는 지정된 파일에 화면을 생성한다.
- 생성한 Figma URL, 화면 수, 생성된 페이지 목록을 반환한다.

하지 않는 일:

- 검수되지 않은 기획을 Figma에 쓰지 않는다.
- 사용자가 제공하지 않은 브랜드 자산을 사실처럼 사용하지 않는다.

### Final Reviewer Agent

책임:

- 기획된 페이지 수와 실제 Figma 화면 수가 일치하는지 확인한다.
- 필수 공통 컴포넌트와 핵심 사용자 흐름이 반영됐는지 확인한다.
- 최종 상태를 `completed`, `needs_revision`, `failed` 중 하나로 반환한다.

## 5. 핵심 계약

모든 Agent 출력은 Pydantic 모델로 검증한다.

### DesignRequest

```json
{
  "service_name": "여행 예약 서비스",
  "target_users": ["국내 여행을 준비하는 사용자"],
  "primary_user_goal": "3번 이내 클릭으로 예약 요청을 완료한다",
  "required_features": ["검색", "상세 보기", "예약 요청"],
  "platforms": ["web", "mobile"]
}
```

### PagePlan

```json
{
  "project_name": "여행 예약 서비스",
  "page_count": 4,
  "pages": [
    {
      "page_id": "search",
      "name": "여행 검색",
      "purpose": "사용자가 조건에 맞는 여행 상품을 찾는다",
      "primary_action": "검색 실행",
      "required_ui": ["검색창", "필터", "결과 카드"]
    }
  ],
  "user_flow": ["search", "detail", "booking", "complete"],
  "shared_components": ["Header", "PrimaryButton", "LoadingState", "ErrorMessage"]
}
```

검증 규칙:

- `page_count`는 `pages`의 실제 항목 수와 같아야 한다.
- `user_flow`의 모든 페이지 ID는 `pages` 안에 존재해야 한다.
- 페이지 ID는 중복될 수 없다.
- 모든 페이지는 목적·핵심 행동·최소 하나의 UI 요소를 가져야 한다.

### UsabilityReview

```json
{
  "passed": true,
  "score": 5,
  "findings": [],
  "checks": {
    "clear_primary_action": true,
    "three_click_goal": true,
    "plain_language": true,
    "error_guidance": true,
    "responsive_design": true,
    "completion_feedback": true
  }
}
```

통과 조건:

- `score`는 1~5 정수다.
- 5점 통과는 여섯 개 체크 항목이 모두 `true`이고 `findings`가 비어 있을 때만 가능하다.
- 보완 필요 결과는 최소 하나의 구체적 개선 항목을 포함한다.

### FigmaBuildResult

```json
{
  "status": "completed",
  "figma_url": "https://www.figma.com/design/...",
  "created_screen_count": 4,
  "created_page_ids": ["search", "detail", "booking", "complete"],
  "error": null
}
```

## 6. API와 Router

FastAPI Router는 `/api` 접두사를 사용한다.

| Method | Path | 목적 |
| --- | --- | --- |
| POST | `/api/designs/plan` | 요구사항으로 PagePlan 생성 |
| POST | `/api/designs/review` | PagePlan UX 검수 |
| POST | `/api/designs/build-figma` | 통과한 PagePlan Figma 생성 |
| POST | `/api/designs/run` | 전체 순차 흐름 실행 |
| GET | `/api/designs/{run_id}` | 현재 상태·Trace·결과 조회 |
| GET | `/api/contracts` | Agent 출력 계약 조회 |
| GET | `/api/health` | 서비스 상태 확인 |

`POST /api/designs/run`은 `DesignRequest`를 받고 Planner → Reviewer → Builder → Final
Reviewer 순서로 실행한다. 어느 계약 검증이든 실패하면 이후 Agent를 실행하지 않고
실패 단계와 원인을 Trace에 기록한다.

## 7. Figma 연동 원칙

- Figma 연결·파일 생성·수정은 사용자가 명시적으로 요청한 경우에만 수행한다.
- 기본 모드는 Figma에 쓰지 않는 `plan_only`다.
- `build_figma` 모드는 UX 검수를 통과한 `PagePlan`만 받는다.
- Figma URL을 실제 결과에서 받기 전에는 URL을 만들거나 추측하지 않는다.
- Figma 연결이 없으면 명확한 오류 상태를 반환하고, 승인된 PagePlan은 그대로 보존한다.

## 8. 데이터와 Trace

각 실행에는 고유 `run_id`를 부여한다. 최소한 아래를 저장·반환한다.

- 요청 시간과 실행 상태
- 현재 Agent와 완료 단계
- 각 Agent의 계약 검증 결과
- 통과·실패·Skip 이유
- 최종 PagePlan, UsabilityReview, FigmaBuildResult

1차 버전은 메모리 저장소로 시작한다. 서버가 재시작되면 Trace가 사라진다는 점을 API와
Swagger 설명에 명시한다. 영구 보관은 후속 버전에서 PostgreSQL 또는 Redis로 확장한다.

## 9. 오류 처리

- 잘못된 입력: FastAPI 422와 필드별 오류를 반환한다.
- 계약 검증 실패: 다음 Agent를 Skip하고 `failed` 상태와 검증 오류를 반환한다.
- Figma 미연결: `failed` 상태와 `figma_not_connected` 오류 코드를 반환한다.
- Figma 쓰기 실패: 원래 PagePlan과 실패 원인을 보존한다.
- 외부 LLM 실패: 성공 데이터로 대체하지 않고 Provider 오류를 Trace에 기록한다.

## 10. 테스트와 제출 증빙

자동 테스트는 최소 다음을 포함한다.

- 페이지 수와 실제 페이지 목록 불일치 차단
- 중복 페이지 ID 차단
- 사용자 흐름에 없는 페이지 참조 차단
- UX 5점 조건 미충족 시 Figma Builder Skip
- Figma 결과 화면 수 불일치 시 Final Review 실패
- 정상 요청이 전체 순차 흐름을 완료

Swagger에서는 다음을 실행해 제출 증빙으로 캡처한다.

1. `GET /api/health`
2. `GET /api/contracts`
3. `POST /api/designs/plan`
4. `POST /api/designs/review`
5. `POST /api/designs/run`의 정상·검수 실패 사례
6. `GET /api/designs/{run_id}` Trace 조회

## 11. 기술 선택

- Python 3.12
- FastAPI + Uvicorn
- Pydantic v2
- pytest
- Figma 연결 도구(연결된 계정이 있을 때만 사용)

새 포트는 임의로 추가하지 않는다. 실행 포트는 프로젝트 README와 환경 변수에 한 곳에서
정의한다.

## 12. 완료 정의

다음 조건을 모두 만족하면 1차 버전을 완료로 본다.

1. Swagger에서 계획·검수·전체 흐름 API를 테스트할 수 있다.
2. 실패한 계약 결과가 다음 Agent로 전달되지 않는다.
3. 정상 흐름은 페이지 수, 사용자 흐름, 만족도 검수 결과를 반환한다.
4. Figma 미연결 상태도 안전하고 이해 가능한 실패로 처리한다.
5. 자동 테스트가 통과한다.
