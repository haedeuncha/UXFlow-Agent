# UXFlow Agent MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI service that plans web pages, recommends safe UI components and icons, validates five-star usability, and only then prepares a Figma build result.

**Architecture:** The API receives a `DesignRequest` and runs deterministic, testable Planner, Component Recommender, UX Reviewer, Figma Builder, and Final Reviewer units. Pydantic contracts guard every handoff. An in-memory run store returns an observable trace; the Figma builder is a safe adapter that returns `figma_not_connected` until an explicit Figma integration is configured.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, Uvicorn, pytest, httpx TestClient.

**Spec:** `docs/superpowers/specs/2026-09-29-uxflow-agent-design.md`

## Global Constraints

- Use Python 3.12, FastAPI, Pydantic v2, and pytest.
- Use the `/api` prefix for all product routes.
- Do not open an additional arbitrary port; configure the server port in one documented location.
- Do not send a failed contract result to a later Agent.
- Default mode is `plan_only`; never write to Figma without explicit `build_figma` mode and a connected integration.
- Only recommend `shadcn/ui`, `Radix UI`, `Lucide`, or `Heroicons` in MVP.
- Never copy third-party code, SVG files, or assets automatically.
- Preserve trace errors; do not replace external Agent failures with fake success data.

## Review Focus

- An empty `required_features` list must be rejected with 422 before any Agent runs.
- A plan whose `page_count` differs from its `pages` length must not reach the reviewer.
- A component recommendation referencing an unknown page ID must be rejected.
- A review marked `passed=true` must fail validation unless all six five-star checks are true and findings are empty.
- A missing Figma connection must return `figma_not_connected` without losing the approved plan or trace.

---

## File Structure

```text
pyproject.toml
README.md
app/
  main.py                         # FastAPI application and router registration
  schemas/contracts.py            # Pydantic input, output, and invariant models
  agents/planner.py               # Requirements -> PagePlan
  agents/component_recommender.py # PagePlan -> ComponentRecommendation
  agents/ux_reviewer.py           # Plan + recommendations -> UsabilityReview
  agents/figma_builder.py         # Approved data -> FigmaBuildResult
  agents/final_reviewer.py        # Final cross-check
  orchestration/design_flow.py    # Ordered handoffs, guards, trace creation
  storage/run_store.py            # In-memory run persistence
  routers/designs.py              # Swagger endpoints
tests/
  test_contracts.py
  test_component_recommender.py
  test_design_flow.py
  test_api.py
```

## Task 1: Project foundation and health endpoint

**Files:**
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `tests/test_api.py`
- Create: `README.md`

**Interfaces:**
- Produces: `app.main.app`, a FastAPI object used by every API test.

- [ ] **Step 1: Write the failing health test**

```python
from fastapi.testclient import TestClient
from app.main import app

def test_health_returns_service_name() -> None:
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "UXFlow Agent"}
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest tests/test_api.py::test_health_returns_service_name -v`

Expected: FAIL because `app.main` does not exist.

- [ ] **Step 3: Add the minimal dependencies and application**

```toml
[project]
name = "uxflow-agent"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["fastapi>=0.115", "uvicorn[standard]>=0.30", "pydantic>=2.9"]

[project.optional-dependencies]
dev = ["pytest>=8.3", "httpx>=0.27"]

[tool.pytest.ini_options]
pythonpath = ["."]
```

```python
# app/main.py
from fastapi import FastAPI

app = FastAPI(title="UXFlow Agent", version="0.1.0")

@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "UXFlow Agent"}
```

- [ ] **Step 4: Run the test and verify it passes**

Run: `python -m pytest tests/test_api.py::test_health_returns_service_name -v`

Expected: PASS.

- [ ] **Step 5: Document the single server command**

Add this README section:

```markdown
## Run

```powershell
python -m uvicorn app.main:app --port 8000
```

Open Swagger at `http://127.0.0.1:8000/docs`.
```

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml README.md app tests/test_api.py
git commit -m "feat: add FastAPI application foundation"
```

## Task 2: Define and validate all handoff contracts

**Files:**
- Create: `app/schemas/__init__.py`
- Create: `app/schemas/contracts.py`
- Create: `tests/test_contracts.py`

**Interfaces:**
- Produces: `DesignRequest`, `PageDefinition`, `PagePlan`, `ComponentRecommendation`, `UsabilityReview`, `FigmaBuildResult`, `DesignRunResult`.
- Consumes: no earlier business interfaces.

- [ ] **Step 1: Write failing invariant tests**

```python
import pytest
from pydantic import ValidationError
from app.schemas.contracts import PageDefinition, PagePlan, UsabilityChecks, UsabilityReview

def test_page_count_must_match_page_list() -> None:
    with pytest.raises(ValidationError, match="page_count"):
        PagePlan(
            project_name="예약 서비스", page_count=2,
            pages=[PageDefinition(page_id="search", name="검색", purpose="검색", primary_action="찾기", required_ui=["검색창"])],
            user_flow=["search"], shared_components=["Header"],
        )

def test_five_star_review_requires_every_check() -> None:
    with pytest.raises(ValidationError, match="five-star"):
        UsabilityReview(
            passed=True, score=5, findings=[],
            checks=UsabilityChecks(error_guidance=False),
        )
```

- [ ] **Step 2: Run the contract tests and verify they fail**

Run: `python -m pytest tests/test_contracts.py -v`

Expected: FAIL because `app.schemas.contracts` does not exist.

- [ ] **Step 3: Implement the contracts and model validators**

```python
class PagePlan(BaseModel):
    project_name: str = Field(min_length=1)
    page_count: int = Field(ge=1, le=30)
    pages: list[PageDefinition] = Field(min_length=1, max_length=30)
    user_flow: list[str] = Field(min_length=1)
    shared_components: list[str]

    @model_validator(mode="after")
    def validate_plan(self) -> "PagePlan":
        ids = [page.page_id for page in self.pages]
        if self.page_count != len(self.pages):
            raise ValueError("page_count must match pages length")
        if len(ids) != len(set(ids)):
            raise ValueError("page_id values must be unique")
        if missing := set(self.user_flow) - set(ids):
            raise ValueError(f"user_flow contains unknown page ids: {sorted(missing)}")
        return self
```

Implement `UsabilityChecks` with all six boolean fields defaulting to `False`; implement
`UsabilityReview` so `passed=True, score=5` requires every check true and no findings.

- [ ] **Step 4: Add the remaining contract tests**

```python
def test_unknown_user_flow_page_is_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown page ids"):
        PagePlan(
            project_name="X", page_count=1,
            pages=[PageDefinition(page_id="home", name="홈", purpose="시작", primary_action="계속", required_ui=["버튼"])],
            user_flow=["missing"], shared_components=[],
        )

def test_failed_review_requires_actionable_finding() -> None:
    with pytest.raises(ValidationError, match="finding"):
        UsabilityReview(passed=False, score=3, findings=[], checks=UsabilityChecks())
```

- [ ] **Step 5: Run all contract tests**

Run: `python -m pytest tests/test_contracts.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/schemas tests/test_contracts.py
git commit -m "feat: add validated UXFlow contracts"
```

## Task 3: Build the component and icon recommendation Agent

**Files:**
- Create: `app/agents/__init__.py`
- Create: `app/agents/component_recommender.py`
- Create: `tests/test_component_recommender.py`

**Interfaces:**
- Consumes: `PagePlan`.
- Produces: `ComponentRecommendation`.
- Signature: `recommend_components(plan: PagePlan) -> ComponentRecommendation`.

- [ ] **Step 1: Write failing recommendation tests**

```python
from app.agents.component_recommender import recommend_components

def test_search_page_gets_search_component_and_icon(plan) -> None:
    result = recommend_components(plan)
    search = next(item for item in result.page_components if item.page_id == "search")
    assert "SearchInput" in search.components
    assert "Search" in search.icons
    assert result.recommended_sources == ["shadcn/ui", "Lucide"]

def test_unknown_component_page_is_rejected(plan) -> None:
    with pytest.raises(ValidationError, match="unknown page"):
        ComponentRecommendation(page_components=[PageComponentRecommendation(page_id="missing", components=["Card"], icons=[])])
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `python -m pytest tests/test_component_recommender.py -v`

Expected: FAIL because the recommender module does not exist.

- [ ] **Step 3: Implement a small deterministic catalog**

```python
KEYWORD_RULES = {
    "search": (["SearchInput", "FilterSheet", "ResultCard"], ["Search", "SlidersHorizontal"]),
    "detail": (["Card", "Tabs", "PrimaryButton"], ["MapPin", "ChevronRight"]),
    "complete": (["SuccessPanel", "PrimaryButton"], ["CircleCheck"]),
}

def recommend_components(plan: PagePlan) -> ComponentRecommendation:
    entries = []
    for page in plan.pages:
        components, icons = KEYWORD_RULES.get(page.page_id, (["Card", "PrimaryButton"], ["Circle"] ))
        entries.append(PageComponentRecommendation(
            page_id=page.page_id, components=components, icons=icons,
            accessibility_notes=["모든 아이콘 버튼에는 접근 가능한 이름을 제공한다."],
        ))
    return ComponentRecommendation(
        page_ids=[page.page_id for page in plan.pages],
        recommended_sources=["shadcn/ui", "Lucide"], page_components=entries,
        shared_components=plan.shared_components, license_review_required=True,
    )
```

- [ ] **Step 4: Verify recommendation tests pass**

Run: `python -m pytest tests/test_component_recommender.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agents/component_recommender.py tests/test_component_recommender.py app/schemas/contracts.py
git commit -m "feat: recommend safe UI components and icons"
```

## Task 4: Implement planner, UX reviewer, Figma-safe builder, and final reviewer

**Files:**
- Create: `app/agents/planner.py`
- Create: `app/agents/ux_reviewer.py`
- Create: `app/agents/figma_builder.py`
- Create: `app/agents/final_reviewer.py`
- Create: `tests/test_design_flow.py`

**Interfaces:**
- `create_page_plan(request: DesignRequest) -> PagePlan`
- `review_usability(plan: PagePlan, recommendation: ComponentRecommendation) -> UsabilityReview`
- `build_figma(plan: PagePlan, mode: Literal["plan_only", "build_figma"]) -> FigmaBuildResult`
- `final_review(plan: PagePlan, build: FigmaBuildResult) -> FinalReview`

- [ ] **Step 1: Write the safety-first failing tests**

```python
def test_low_score_review_has_concrete_finding(plan, recommendation) -> None:
    review = review_usability(plan, recommendation)
    assert review.passed is False
    assert review.findings == ["완료 화면과 완료 피드백이 필요합니다."]

def test_plan_only_never_creates_figma_url(plan) -> None:
    result = build_figma(plan, mode="plan_only")
    assert result.status == "skipped"
    assert result.figma_url is None

def test_build_mode_without_connection_preserves_error(plan) -> None:
    result = build_figma(plan, mode="build_figma")
    assert result.status == "failed"
    assert result.error_code == "figma_not_connected"
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `python -m pytest tests/test_design_flow.py -v`

Expected: FAIL because the Agent modules do not exist.

- [ ] **Step 3: Implement deterministic MVP behavior**

```python
def build_figma(plan: PagePlan, mode: str) -> FigmaBuildResult:
    if mode == "plan_only":
        return FigmaBuildResult(status="skipped", figma_url=None, created_screen_count=0,
                                created_page_ids=[], error_code=None)
    return FigmaBuildResult(status="failed", figma_url=None, created_screen_count=0,
                            created_page_ids=[], error_code="figma_not_connected")
```

Planner must make one page per required feature, add a final `complete` page, and create a
linear `user_flow`. UX Reviewer must require a clear primary action, 3-click goal statement,
plain-language labels, error guidance, mobile support, and completion feedback. Final Reviewer
must fail when `created_screen_count != plan.page_count`.

- [ ] **Step 4: Add normal-path tests**

```python
def test_planner_adds_completion_page() -> None:
    plan = create_page_plan(sample_request())
    assert plan.user_flow[-1] == "complete"

def test_final_reviewer_rejects_screen_count_mismatch(plan) -> None:
    result = final_review(plan, FigmaBuildResult(status="completed", figma_url="https://figma.test/x", created_screen_count=1, created_page_ids=["search"], error_code=None))
    assert result.status == "needs_revision"
```

- [ ] **Step 5: Run Agent tests**

Run: `python -m pytest tests/test_design_flow.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/agents tests/test_design_flow.py
git commit -m "feat: add guarded UXFlow agents"
```

## Task 5: Orchestrate guarded handoffs and persist trace state

**Files:**
- Create: `app/storage/__init__.py`
- Create: `app/storage/run_store.py`
- Create: `app/orchestration/__init__.py`
- Create: `app/orchestration/design_flow.py`
- Modify: `tests/test_design_flow.py`

**Interfaces:**
- `run_design_flow(request: DesignRequest, mode: str) -> DesignRunResult`
- `get_run(run_id: str) -> DesignRunResult | None`

- [ ] **Step 1: Write the failing orchestration tests**

```python
def test_failed_usability_review_skips_figma_builder(monkeypatch) -> None:
    monkeypatch.setattr("app.orchestration.design_flow.review_usability", lambda *_: failing_review())
    result = run_design_flow(sample_request(), mode="build_figma")
    assert result.status == "needs_revision"
    assert "figma_builder:skipped" in result.trace

def test_completed_run_is_retrievable() -> None:
    result = run_design_flow(sample_request(), mode="plan_only")
    assert get_run(result.run_id) == result
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `python -m pytest tests/test_design_flow.py -v`

Expected: FAIL because the orchestration and storage modules do not exist.

- [ ] **Step 3: Implement the ordered guard clauses**

```python
def run_design_flow(request: DesignRequest, mode: str) -> DesignRunResult:
    trace = ["planner:started"]
    plan = create_page_plan(request)
    trace.append("planner:verified")
    recommendation = recommend_components(plan)
    trace.append("component_recommender:verified")
    review = review_usability(plan, recommendation)
    if not review.passed:
        result = DesignRunResult.new("needs_revision", trace + ["ux_reviewer:needs_revision", "figma_builder:skipped"], plan, recommendation, review, None, None)
        return save_run(result)
    build = build_figma(plan, mode)
    trace.append(f"figma_builder:{build.status}")
    final = final_review(plan, build) if build.status == "completed" else None
    return save_run(DesignRunResult.new("completed" if mode == "plan_only" else build.status, trace, plan, recommendation, review, build, final))
```

- [ ] **Step 4: Run orchestration tests**

Run: `python -m pytest tests/test_design_flow.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/orchestration app/storage tests/test_design_flow.py
git commit -m "feat: orchestrate validated design flow"
```

## Task 6: Add Swagger router, endpoint tests, and submission instructions

**Files:**
- Create: `app/routers/__init__.py`
- Create: `app/routers/designs.py`
- Modify: `app/main.py`
- Modify: `tests/test_api.py`
- Modify: `README.md`

**Interfaces:**
- Produces: `POST /api/designs/plan`, `/recommend-components`, `/review`, `/run`; `GET /api/designs/{run_id}`, `/contracts`, `/health`.

- [ ] **Step 1: Write failing API tests**

```python
def test_plan_endpoint_returns_page_count() -> None:
    response = TestClient(app).post("/api/designs/plan", json={
        "service_name": "예약", "target_users": ["여행자"],
        "primary_user_goal": "예약 완료", "required_features": ["검색"], "platforms": ["web"],
    })
    assert response.status_code == 200
    assert response.json()["page_count"] == 2

def test_contracts_endpoint_lists_page_plan() -> None:
    response = TestClient(app).get("/api/contracts")
    assert response.status_code == 200
    assert "PagePlan" in response.json()

def test_run_lookup_returns_trace() -> None:
    client = TestClient(app)
    run = client.post("/api/designs/run", json={
        "service_name": "예약", "target_users": ["여행자"],
        "primary_user_goal": "예약 완료", "required_features": ["검색"], "platforms": ["web"],
    }).json()
    response = client.get(f"/api/designs/{run['run_id']}")
    assert response.status_code == 200
    assert "planner:verified" in response.json()["trace"]
```

- [ ] **Step 2: Run API tests and verify they fail**

Run: `python -m pytest tests/test_api.py -v`

Expected: FAIL because the design routes are not registered.

- [ ] **Step 3: Implement routes with response models**

```python
router = APIRouter(prefix="/api", tags=["UXFlow Agent"])

@router.post("/designs/plan", response_model=PagePlan)
def create_plan(request: DesignRequest) -> PagePlan:
    return create_page_plan(request)

@router.post("/designs/run", response_model=DesignRunResult)
def run_design(request: DesignRequest, mode: Literal["plan_only", "build_figma"] = "plan_only") -> DesignRunResult:
    return run_design_flow(request, mode)

@router.get("/designs/{run_id}", response_model=DesignRunResult)
def read_run(run_id: str) -> DesignRunResult:
    if result := get_run(run_id):
        return result
    raise HTTPException(status_code=404, detail="run_id를 찾을 수 없습니다.")
```

Register `router` in `app/main.py`. Implement `/contracts` by returning JSON schemas with
`PagePlan.model_json_schema()` and the other public contract models.

- [ ] **Step 4: Run all tests**

Run: `python -m pytest -v`

Expected: PASS.

- [ ] **Step 5: Update README with Swagger evidence steps**

Add an ordered section using these exact requests:

```text
GET  /api/health
GET  /api/contracts
POST /api/designs/plan
POST /api/designs/recommend-components
POST /api/designs/review
POST /api/designs/run?mode=plan_only
GET  /api/designs/{run_id}
```

State that `build_figma` returns `figma_not_connected` until a user explicitly connects Figma.

- [ ] **Step 6: Commit**

```bash
git add app/main.py app/routers tests/test_api.py README.md
git commit -m "feat: expose UXFlow design APIs"
```

## Final Verification

- [ ] Run `python -m pytest -v` and verify all tests pass.
- [ ] Run `python -m uvicorn app.main:app --port 8000` without selecting a new port.
- [ ] Open `/docs` and execute the seven README evidence requests.
- [ ] Capture one successful `plan_only` run and one UX-review failure showing `figma_builder:skipped`.
- [ ] Verify `git status --short` is empty.
- [ ] Push the completed branch to `origin/main`.
