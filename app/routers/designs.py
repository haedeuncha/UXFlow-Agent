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


router = APIRouter(prefix="/api", tags=["UXFlow Agent API"])


@router.get(
    "/figma/status",
    summary="Figma 토큰 설정 상태 확인",
    description="개인 토큰 값은 반환하지 않고 설정 여부만 확인합니다.",
)
def get_figma_status() -> dict[str, bool]:
    """개인 토큰을 노출하지 않고 로컬 설정 상태를 확인합니다."""
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
            raise ValueError("추천 결과의 페이지 ID는 화면 계획의 페이지 ID와 같아야 합니다.")
        return self


@router.post(
    "/designs/plan",
    response_model=PagePlan,
    summary="화면 계획 생성",
    description="서비스 요구사항을 페이지 목록, 화면 수, 사용자 흐름으로 변환합니다.",
)
def create_plan(request: DesignRequest) -> PagePlan:
    """서비스 요구사항에서 화면 계획을 생성합니다."""
    return create_page_plan(request)


@router.post(
    "/designs/recommend-components",
    response_model=ComponentRecommendation,
    summary="UI 컴포넌트와 아이콘 추천",
    description="검증된 화면 계획의 페이지별 UI 컴포넌트와 아이콘을 추천합니다.",
)
def create_recommendation(plan: PagePlan) -> ComponentRecommendation:
    """각 화면에 허용된 UI 컴포넌트와 아이콘 소스를 추천합니다."""
    return recommend_components(plan)


@router.post(
    "/designs/review",
    response_model=UsabilityReview,
    summary="UX 5점 기준 검수",
    description="화면 계획과 컴포넌트 추천 결과를 6개 사용성 기준으로 검수합니다.",
)
def review_design(request: ReviewRequest) -> UsabilityReview:
    """화면 계획을 5점 사용성 기준으로 검수합니다."""
    return review_usability(request.plan, request.recommendation)


@router.post(
    "/designs/run",
    response_model=DesignRunResult,
    summary="전체 Agent 흐름 실행",
    description="계획, 추천, UX 검수를 순서대로 실행하고 처리 기록을 저장합니다.",
)
def run_design(
    request: DesignRequest,
    mode: Literal["plan_only", "build_figma"] = "plan_only",
) -> DesignRunResult:
    """검증된 Agent 흐름을 실행하고 확인 가능한 처리 기록을 저장합니다."""
    return run_design_flow(request, mode)


@router.get(
    "/designs/{run_id}",
    response_model=DesignRunResult,
    summary="실행 결과와 처리 기록 조회",
    description="이전에 실행한 전체 Agent 흐름의 결과와 Trace를 조회합니다.",
)
def read_run(run_id: str) -> DesignRunResult:
    """run_id로 메모리에 저장된 실행 결과를 조회합니다."""
    result = get_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="run_id를 찾을 수 없습니다.")
    return result


@router.get(
    "/contracts",
    summary="Agent 데이터 계약 조회",
    description="Agent 사이에서 주고받는 입력과 출력의 JSON Schema를 반환합니다.",
)
def read_contracts() -> dict[str, dict[str, object]]:
    """공개 Agent 흐름의 JSON Schema를 반환합니다."""
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
