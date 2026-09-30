"""Pydantic models for the data exchanged between UXFlow agents."""

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class HandoffModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DesignRequest(HandoffModel):
    service_name: NonEmptyText
    target_users: list[NonEmptyText] = Field(min_length=1)
    primary_user_goal: NonEmptyText
    required_features: list[NonEmptyText] = Field(min_length=1)
    platforms: list[Literal["web", "mobile"]] = Field(min_length=1)


class PageDefinition(HandoffModel):
    page_id: NonEmptyText
    name: NonEmptyText
    purpose: NonEmptyText
    primary_action: NonEmptyText
    required_ui: list[NonEmptyText] = Field(min_length=1)


class PagePlan(HandoffModel):
    project_name: NonEmptyText
    page_count: int = Field(ge=1, le=30)
    pages: list[PageDefinition] = Field(min_length=1, max_length=30)
    user_flow: list[NonEmptyText] = Field(min_length=1)
    shared_components: list[NonEmptyText]

    @model_validator(mode="after")
    def validate_plan(self) -> "PagePlan":
        ids = [page.page_id for page in self.pages]
        if self.page_count != len(self.pages):
            raise ValueError("페이지 수(page_count)는 pages 항목 수와 같아야 합니다.")
        if len(ids) != len(set(ids)):
            raise ValueError("페이지 ID(page_id)는 중복될 수 없습니다.")
        if missing := set(self.user_flow) - set(ids):
            raise ValueError(f"사용자 흐름에 없는 페이지 ID가 있습니다: {sorted(missing)}")
        return self


class PageComponentRecommendation(HandoffModel):
    page_id: NonEmptyText
    components: list[NonEmptyText] = Field(default_factory=list)
    icons: list[NonEmptyText] = Field(default_factory=list)
    accessibility_notes: list[NonEmptyText] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_assets(self) -> "PageComponentRecommendation":
        if not self.components and not self.icons:
            raise ValueError("각 페이지에는 컴포넌트 또는 아이콘이 하나 이상 필요합니다.")
        return self


ALLOWED_RECOMMENDATION_SOURCES = frozenset({"shadcn/ui", "Radix UI", "Lucide", "Heroicons"})


class ComponentRecommendation(HandoffModel):
    page_ids: list[NonEmptyText] = Field(default_factory=list)
    recommended_sources: list[NonEmptyText] = Field(default_factory=list)
    page_components: list[PageComponentRecommendation]
    shared_components: list[NonEmptyText] = Field(default_factory=list)
    license_review_required: bool = True

    @model_validator(mode="after")
    def validate_recommendation(self) -> "ComponentRecommendation":
        unknown_pages = {item.page_id for item in self.page_components} - set(self.page_ids)
        if unknown_pages:
            raise ValueError(f"추천 결과에 화면 계획에 없는 페이지 ID가 있습니다: {sorted(unknown_pages)}")
        if not self.page_ids:
            raise ValueError("page_ids에는 화면 계획의 페이지 ID를 지정해야 합니다.")
        if len(self.page_ids) != len(set(self.page_ids)):
            raise ValueError("page_ids는 중복될 수 없습니다.")
        recommended_ids = [item.page_id for item in self.page_components]
        if len(recommended_ids) != len(set(recommended_ids)):
            raise ValueError("page_components의 페이지 ID는 중복될 수 없습니다.")
        if missing_pages := set(self.page_ids) - set(recommended_ids):
            raise ValueError(f"추천 결과에 누락된 페이지 ID가 있습니다: {sorted(missing_pages)}")
        if not self.recommended_sources:
            raise ValueError("추천 소스(recommended_sources)는 비어 있을 수 없습니다.")
        if unknown_sources := set(self.recommended_sources) - ALLOWED_RECOMMENDATION_SOURCES:
            raise ValueError(f"허용되지 않은 추천 소스가 있습니다: {sorted(unknown_sources)}")
        return self


class UsabilityChecks(HandoffModel):
    clear_primary_action: bool = False
    three_click_goal: bool = False
    plain_language: bool = False
    error_guidance: bool = False
    responsive_design: bool = False
    completion_feedback: bool = False


class UsabilityReview(HandoffModel):
    passed: bool
    score: int = Field(ge=1, le=5)
    findings: list[NonEmptyText]
    checks: UsabilityChecks

    @model_validator(mode="after")
    def validate_review(self) -> "UsabilityReview":
        if self.passed and (
            self.score != 5 or not all(self.checks.model_dump().values()) or self.findings
        ):
            raise ValueError("5점 통과는 모든 UX 점검 항목이 통과하고 개선 사항이 없어야 합니다.")
        if not self.passed and not self.findings:
            raise ValueError("검수 실패 결과에는 실행 가능한 개선 사항이 하나 이상 필요합니다.")
        return self


class FigmaBuildResult(HandoffModel):
    status: Literal["skipped", "completed", "failed"]
    figma_url: str | None = None
    created_screen_count: int = Field(default=0, ge=0)
    created_page_ids: list[NonEmptyText] = Field(default_factory=list)
    error_code: NonEmptyText | None = None
    error: NonEmptyText | None = None

    @model_validator(mode="after")
    def validate_build(self) -> "FigmaBuildResult":
        if self.status == "completed":
            if not self.figma_url:
                raise ValueError("완료된 Figma 결과에는 figma_url이 필요합니다.")
            if self.created_screen_count == 0:
                raise ValueError("완료된 Figma 결과의 생성 화면 수는 1개 이상이어야 합니다.")
            if self.created_screen_count != len(self.created_page_ids):
                raise ValueError("생성 화면 수는 생성된 페이지 ID 수와 같아야 합니다.")
        elif self.status == "skipped":
            if self.figma_url or self.created_screen_count or self.created_page_ids:
                raise ValueError("건너뛴 Figma 결과에는 생성 결과를 포함할 수 없습니다.")
        elif not self.error_code and not self.error:
            raise ValueError("실패한 Figma 결과에는 error_code 또는 error가 필요합니다.")
        return self


class FinalReview(HandoffModel):
    status: Literal["completed", "needs_revision", "failed"]
    findings: list[NonEmptyText] = Field(default_factory=list)


class DesignRunResult(HandoffModel):
    run_id: NonEmptyText
    requested_at: datetime
    status: Literal["completed", "needs_revision", "failed"]
    current_agent: NonEmptyText | None = None
    completed_steps: list[NonEmptyText] = Field(default_factory=list)
    validation_results: dict[str, bool] = Field(default_factory=dict)
    trace: list[NonEmptyText]
    plan: PagePlan | None = None
    recommendation: ComponentRecommendation | None = None
    review: UsabilityReview | None = None
    build: FigmaBuildResult | None = None
    final: FinalReview | None = None

    @model_validator(mode="after")
    def validate_recommendation_matches_plan(self) -> "DesignRunResult":
        if self.plan is not None and self.recommendation is not None:
            plan_ids = {page.page_id for page in self.plan.pages}
            recommendation_ids = set(self.recommendation.page_ids)
            component_ids = {item.page_id for item in self.recommendation.page_components}
            if recommendation_ids != plan_ids or component_ids != plan_ids:
                raise ValueError("추천 결과의 페이지 ID는 화면 계획의 페이지 ID와 같아야 합니다.")
        return self

    @classmethod
    def new(
        cls,
        status: Literal["completed", "needs_revision", "failed"],
        trace: list[str],
        plan: PagePlan | None,
        recommendation: ComponentRecommendation | None,
        review: UsabilityReview | None,
        build: FigmaBuildResult | None,
        final: FinalReview | None,
    ) -> "DesignRunResult":
        completed_steps = [entry for entry in trace if entry.endswith(":verified")]
        validation_results = {
            stage: outcome == "verified"
            for stage, outcome in (entry.split(":", 1) for entry in trace if ":" in entry)
            if outcome in {"verified", "failed"}
        }
        return cls(
            run_id=str(uuid4()),
            requested_at=datetime.now(timezone.utc),
            status=status,
            current_agent=trace[-1].split(":", 1)[0] if trace else None,
            completed_steps=completed_steps,
            validation_results=validation_results,
            trace=trace,
            plan=plan,
            recommendation=recommendation,
            review=review,
            build=build,
            final=final,
        )
