# UXFlow Agent

UXFlow Agent는 웹서비스 요구사항을 받아 **필요한 화면 수·페이지 흐름·공통 UI 컴포넌트**를 제안하고, 사용성 기준을 점검하는 교육용 멀티 에이전트 API입니다.

예를 들어 “여행 예약 서비스에 검색·상세 보기·예약 요청이 필요하다”라고 입력하면, 페이지 계획과 사용자 흐름을 만들고 추천 컴포넌트 및 UX 검수 결과를 돌려줍니다.

> 상세한 기획과 제출 기준은 [프로젝트 계획서](docs/PROJECT_PLAN.md)를 참고하세요.

## 1. 현재 가능한 기능

- 요구사항으로 페이지 목록, 화면 수, 사용자 흐름 생성
- 페이지별 `shadcn/ui`, `Lucide` 기반 컴포넌트·아이콘 추천
- 5점 UX 기준(명확한 행동, 3회 이내 흐름, 오류 안내 등) 검수
- Agent 단계별 계약 검증과 실행 Trace 조회
- Swagger에서 모든 API를 직접 테스트
- Figma 토큰이 설정됐는지 안전하게 확인

## 2. 현재 범위와 주의 사항

- 기본 실행 모드는 `plan_only`이며 Figma 파일을 수정하지 않습니다.
- `build_figma`는 Figma 화면을 실제 생성하는 기능이 아직 연결되지 않았으므로 `figma_not_connected` 상태를 정확히 반환합니다.
- Figma Personal Access Token은 `.env`에만 보관합니다. 토큰을 README, 코드, Swagger 요청, GitHub에 넣으면 안 됩니다.
- 실행 기록은 메모리에만 저장됩니다. 서버를 재시작하면 이전 `run_id` 조회 결과는 사라집니다.

## 3. 처음 실행하기 (Windows PowerShell)

프로젝트 폴더에서 아래 순서대로 실행하세요.

```powershell
cd "C:\UXFlow Agent"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

가상환경이 이미 있다면 `python -m venv .venv` 단계는 건너뛰어도 됩니다.

### Figma 토큰 설정 (선택)

Figma 상태 API를 사용하려면 프로젝트 최상위 폴더에 `.env` 파일을 만들고 다음처럼 입력하세요.

```text
FIGMA_ACCESS_TOKEN=여기에_본인의_Figma_토큰
```

`.env`는 Git이 무시하도록 설정되어 있습니다. 토큰 값은 API 응답에도 표시되지 않고, `GET /api/figma/status`는 설정 여부만 반환합니다.

## 4. 서버 실행

가상환경이 활성화된 상태에서 다음 한 줄을 실행합니다. 이 프로젝트는 **8000 포트만 사용**합니다.

```powershell
python -m uvicorn app.main:app --port 8000
```

브라우저에서 다음 주소를 엽니다.

- Swagger: <http://127.0.0.1:8000/docs>
- 서비스 상태: <http://127.0.0.1:8000/api/health>

서버를 멈추려면 실행 중인 터미널에서 `Ctrl + C`를 누르세요.

## 5. Swagger 테스트 순서

Swagger에서 아래 순서대로 `Try it out` → `Execute`를 누르면 전체 흐름을 확인할 수 있습니다.

1. `GET /api/health` — API가 실행 중인지 확인합니다.
2. `GET /api/figma/status` — Figma 토큰 설정 여부만 확인합니다.
3. `GET /api/contracts` — Agent 간 데이터 계약(JSON Schema)을 확인합니다.
4. `POST /api/designs/plan` — 요구사항으로 화면 계획을 만듭니다.
5. `POST /api/designs/recommend-components` — 4번의 응답 전체를 붙여 넣습니다.
6. `POST /api/designs/review` — 4번의 `plan`과 5번의 `recommendation`을 넣어 UX를 검수합니다.
7. `POST /api/designs/run?mode=plan_only` — 전체 Agent 흐름을 한 번에 실행합니다.
8. `GET /api/designs/{run_id}` — 7번 응답의 `run_id`를 주소에 넣어 Trace를 확인합니다.

### 4번과 7번에 넣을 예시 요청

```json
{
  "service_name": "여행 예약 서비스",
  "target_users": ["국내 여행을 준비하는 사용자"],
  "primary_user_goal": "검색 후 예약 요청을 완료한다",
  "required_features": ["검색", "상세 보기", "예약 요청"],
  "platforms": ["web", "mobile"]
}
```

### 정상 결과에서 볼 항목

- `page_count`: 만들어진 화면 수
- `user_flow`: 사용자가 이동하는 페이지 순서
- `shared_components`: 여러 화면에서 재사용할 UI
- `passed`, `score`: UX 검수 통과 여부와 점수
- `trace`: Planner → Component Recommender → UX Reviewer 순서의 처리 기록

## 6. 자동 테스트

서버를 켜지 않아도 아래 명령으로 검증할 수 있습니다.

```powershell
python -m pytest -q
```

현재 테스트는 계약 검증, Agent 흐름, API 응답, Figma 토큰 노출 방지 동작을 확인합니다.

## 7. 자주 발생하는 문제

| 상황 | 확인 방법 |
| --- | --- |
| `No module named app` | 반드시 `C:\UXFlow Agent` 폴더에서 명령을 실행하고 가상환경을 활성화하세요. |
| `python`을 찾을 수 없음 | Python 3.12 설치 여부를 확인한 뒤 터미널을 새로 여세요. |
| Swagger가 열리지 않음 | 서버 터미널에 오류가 없는지 보고 `http://127.0.0.1:8000/docs` 주소를 다시 여세요. |
| Figma 상태가 `false` | 프로젝트 최상위 `.env` 파일의 `FIGMA_ACCESS_TOKEN=` 뒤에 토큰이 있는지 확인하세요. 토큰 자체를 공유하지 마세요. |
| `figma_not_connected` | 현재 MVP의 정상적인 안내입니다. 실제 Figma 화면 생성 연결은 다음 개발 단계입니다. |

## 8. 프로젝트 구조

```text
app/
  agents/          # Planner, 추천, UX 검수, Figma 안전 어댑터
  orchestration/   # Agent 실행 순서와 Trace 관리
  routers/         # Swagger API 경로
  schemas/         # Pydantic 계약(입력·출력 검증)
  storage/         # 실행 결과의 메모리 저장소
docs/
  PROJECT_PLAN.md  # 제출·설명용 프로젝트 계획서
tests/             # 자동 테스트
```

## 9. 관련 문서

- [프로젝트 계획서](docs/PROJECT_PLAN.md): 목표, Agent 흐름, 현재 상태, 다음 단계, 제출 체크리스트
- [기술 설계서](docs/superpowers/specs/2026-09-29-uxflow-agent-design.md): 계약과 API의 상세 설계
- [초기 구현 계획](docs/superpowers/plans/2026-09-29-uxflow-agent-mvp.md): MVP를 만들 때 사용한 작업 계획
