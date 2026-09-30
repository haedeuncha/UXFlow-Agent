"""Swagger-visible endpoints for the deterministic UXFlow workflow."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_validator

from app.agents.component_recommender import recommend_components
from app.agents.planner import create_page_plan
from app.agents.ux_reviewer import review_usability
from app.config import figma_token_configured
from app.orchestration.design_flow import get_run, run_design_flow
from app.schemas.contracts import (
    ComponentRecommendation,
    DesignRequest,
    DesignRunResult,
    FigmaBuildResult,
    FinalReview,
    PagePlan,
    UsabilityReview,
)


router = APIRouter(prefix="/api", tags=["UXFlow Agent"])


@router.get("/figma/status")
def get_figma_status() -> dict[str, bool]:
    """Confirm local configuration without exposing a personal access token."""
    return {"configured": figma_token_configured()}


class ReviewRequest(BaseModel):
    """The two validated handoffs consumed by the usability reviewer."""

    plan: PagePlan
    recommendation: ComponentRecommendation

    @model_validator(mode="after")
    def validate_recommendation_matches_plan(self) -> "ReviewRequest":
        plan_ids = {page.page_id for page in self.plan.pages}
        recommendation_ids = set(self.recommendation.page_ids)
        component_ids = {
            item.page_id for item in self.recommendation.page_components
        }
        if recommendation_ids != plan_ids or component_ids != plan_ids:
            raise ValueError("recommendation page ids must match plan page ids")
        return self


@router.post("/designs/plan", response_model=PagePlan)
def create_plan(request: DesignRequest) -> PagePlan:
    """Create the page plan from a service brief."""
    return create_page_plan(request)


@router.post("/designs/recommend-components", response_model=ComponentRecommendation)
def create_recommendation(plan: PagePlan) -> ComponentRecommendation:
    """Recommend only approved component and icon sources for every page."""
    return recommend_components(plan)


@router.post("/designs/review", response_model=UsabilityReview)
def review_design(request: ReviewRequest) -> UsabilityReview:
    """Check the page plan against the five-star usability requirements."""
    return review_usability(request.plan, request.recommendation)


@router.post("/designs/run", response_model=DesignRunResult)
def run_design(
    request: DesignRequest,
    mode: Literal["plan_only", "build_figma"] = "plan_only",
) -> DesignRunResult:
    """Run all guarded Agent handoffs and save the observable trace."""
    return run_design_flow(request, mode)


@router.get("/designs/{run_id}", response_model=DesignRunResult)
def read_run(run_id: str) -> DesignRunResult:
    """Read one in-memory design-flow result by its run identifier."""
    result = get_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="run_id를 찾을 수 없습니다.")
    return result


@router.get("/contracts")
def read_contracts() -> dict[str, dict[str, object]]:
    """Expose JSON Schema for the public workflow handoffs."""
    models = (
        DesignRequest,
        PagePlan,
        ComponentRecommendation,
        UsabilityReview,
        FigmaBuildResult,
        FinalReview,
        DesignRunResult,
    )
    return {model.__name__: model.model_json_schema() for model in models}
