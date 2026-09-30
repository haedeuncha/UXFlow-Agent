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
            raise ValueError("page_count must match pages length")
        if len(ids) != len(set(ids)):
            raise ValueError("page_id values must be unique")
        if missing := set(self.user_flow) - set(ids):
            raise ValueError(f"user_flow contains unknown page ids: {sorted(missing)}")
        return self


class PageComponentRecommendation(HandoffModel):
    page_id: NonEmptyText
    components: list[NonEmptyText] = Field(default_factory=list)
    icons: list[NonEmptyText] = Field(default_factory=list)
    accessibility_notes: list[NonEmptyText] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_assets(self) -> "PageComponentRecommendation":
        if not self.components and not self.icons:
            raise ValueError("page needs at least one component or icon")
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
            raise ValueError(f"recommendation references unknown page ids: {sorted(unknown_pages)}")
        if not self.page_ids:
            raise ValueError("page_ids must identify the PagePlan pages")
        if len(self.page_ids) != len(set(self.page_ids)):
            raise ValueError("page_ids must be unique")
        recommended_ids = [item.page_id for item in self.page_components]
        if len(recommended_ids) != len(set(recommended_ids)):
            raise ValueError("page_components must have unique page ids")
        if missing_pages := set(self.page_ids) - set(recommended_ids):
            raise ValueError(f"recommendation is missing page ids: {sorted(missing_pages)}")
        if not self.recommended_sources:
            raise ValueError("recommended_sources must not be empty")
        if unknown_sources := set(self.recommended_sources) - ALLOWED_RECOMMENDATION_SOURCES:
            raise ValueError(f"unapproved recommendation source: {sorted(unknown_sources)}")
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
            raise ValueError("five-star review requires all checks and no findings")
        if not self.passed and not self.findings:
            raise ValueError("failed review requires an actionable finding")
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
                raise ValueError("completed result requires figma_url")
            if self.created_screen_count == 0:
                raise ValueError("completed result requires created_screen_count above zero")
            if self.created_screen_count != len(self.created_page_ids):
                raise ValueError("created_screen_count must match created_page_ids")
        elif self.status == "skipped":
            if self.figma_url or self.created_screen_count or self.created_page_ids:
                raise ValueError("skipped result cannot claim Figma output")
        elif not self.error_code and not self.error:
            raise ValueError("failed result requires an error_code or error")
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
                raise ValueError("recommendation page ids must match PagePlan page ids")
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
