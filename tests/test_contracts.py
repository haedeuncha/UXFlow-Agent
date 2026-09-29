import pytest
from pydantic import ValidationError

from app.schemas.contracts import (
    ComponentRecommendation,
    DesignRequest,
    DesignRunResult,
    FigmaBuildResult,
    FinalReview,
    PageComponentRecommendation,
    PageDefinition,
    PagePlan,
    UsabilityChecks,
    UsabilityReview,
)


def sample_page(page_id: str = "home") -> PageDefinition:
    return PageDefinition(
        page_id=page_id,
        name="홈",
        purpose="시작",
        primary_action="계속",
        required_ui=["버튼"],
    )


def sample_plan() -> PagePlan:
    return PagePlan(
        project_name="예약 서비스",
        page_count=1,
        pages=[sample_page()],
        user_flow=["home"],
        shared_components=["Header"],
    )


def test_page_count_must_match_page_list() -> None:
    with pytest.raises(ValidationError, match="page_count"):
        PagePlan(
            project_name="예약 서비스",
            page_count=2,
            pages=[
                PageDefinition(
                    page_id="search",
                    name="검색",
                    purpose="검색",
                    primary_action="찾기",
                    required_ui=["검색창"],
                )
            ],
            user_flow=["search"],
            shared_components=["Header"],
        )


def test_five_star_review_requires_every_check() -> None:
    with pytest.raises(ValidationError, match="five-star"):
        UsabilityReview(
            passed=True,
            score=5,
            findings=[],
            checks=UsabilityChecks(error_guidance=False),
        )


def test_duplicate_page_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="page_id values must be unique"):
        PagePlan(
            project_name="X",
            page_count=2,
            pages=[sample_page(), sample_page()],
            user_flow=["home"],
            shared_components=[],
        )


def test_unknown_user_flow_page_is_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown page ids"):
        PagePlan(
            project_name="X",
            page_count=1,
            pages=[sample_page()],
            user_flow=["missing"],
            shared_components=[],
        )


@pytest.mark.parametrize("field,value", [("purpose", " "), ("primary_action", ""), ("required_ui", [])])
def test_page_requires_purpose_action_and_ui(field: str, value: object) -> None:
    data = sample_page().model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        PageDefinition.model_validate(data)


def test_request_requires_a_goal_and_feature() -> None:
    with pytest.raises(ValidationError):
        DesignRequest(
            service_name="예약",
            target_users=["여행자"],
            primary_user_goal=" ",
            required_features=[],
            platforms=["web"],
        )


def test_recommendation_rejects_unknown_page() -> None:
    with pytest.raises(ValidationError, match="unknown page"):
        ComponentRecommendation(
            page_ids=["home"],
            recommended_sources=["Lucide"],
            page_components=[PageComponentRecommendation(page_id="missing", components=["Card"], icons=[])],
            shared_components=[],
        )


def test_recommendation_rejects_unapproved_source() -> None:
    with pytest.raises(ValidationError, match="source"):
        ComponentRecommendation(
            page_ids=["home"],
            recommended_sources=["Unknown UI Kit"],
            page_components=[PageComponentRecommendation(page_id="home", components=["Card"], icons=[])],
            shared_components=[],
        )


def test_recommendation_covers_every_planned_page() -> None:
    with pytest.raises(ValidationError, match="missing page"):
        ComponentRecommendation(
            page_ids=["home", "complete"],
            recommended_sources=["Lucide"],
            page_components=[PageComponentRecommendation(page_id="home", components=["Card"], icons=[])],
            shared_components=[],
        )


def test_page_recommendation_needs_component_or_icon() -> None:
    with pytest.raises(ValidationError, match="component or icon"):
        PageComponentRecommendation(page_id="home", components=[], icons=[])


def test_failed_review_requires_actionable_finding() -> None:
    with pytest.raises(ValidationError, match="finding"):
        UsabilityReview(passed=False, score=3, findings=[], checks=UsabilityChecks())


def test_five_star_review_rejects_findings() -> None:
    with pytest.raises(ValidationError, match="five-star"):
        UsabilityReview(
            passed=True,
            score=5,
            findings=["완료 안내 추가"],
            checks=UsabilityChecks(
                clear_primary_action=True,
                three_click_goal=True,
                plain_language=True,
                error_guidance=True,
                responsive_design=True,
                completion_feedback=True,
            ),
        )


def test_completed_figma_result_needs_real_url_and_matching_pages() -> None:
    with pytest.raises(ValidationError, match="figma_url"):
        FigmaBuildResult(status="completed", created_screen_count=1, created_page_ids=["home"])
    with pytest.raises(ValidationError, match="created_screen_count"):
        FigmaBuildResult(
            status="completed",
            figma_url="https://www.figma.com/design/abc",
            created_screen_count=2,
            created_page_ids=["home"],
        )


def test_completed_figma_result_requires_a_screen() -> None:
    with pytest.raises(ValidationError, match="created_screen_count"):
        FigmaBuildResult(status="completed", figma_url="https://www.figma.com/design/abc")


def test_plan_only_build_result_cannot_claim_figma_output() -> None:
    with pytest.raises(ValidationError, match="skipped"):
        FigmaBuildResult(
            status="skipped",
            figma_url="https://www.figma.com/design/abc",
            created_screen_count=1,
            created_page_ids=["home"],
        )


def test_design_run_result_new_preserves_validated_handoffs() -> None:
    plan = sample_plan()
    recommendation = ComponentRecommendation(
        page_ids=["home"],
        recommended_sources=["shadcn/ui", "Lucide"],
        page_components=[PageComponentRecommendation(page_id="home", components=["Card"], icons=[])],
        shared_components=["Header"],
    )
    review = UsabilityReview(passed=False, score=3, findings=["완료 피드백 추가"], checks=UsabilityChecks())
    result = DesignRunResult.new("needs_revision", ["planner:verified"], plan, recommendation, review, None, None)
    assert result.run_id
    assert result.plan == plan
    assert result.recommendation == recommendation
    assert result.review == review
    assert result.trace == ["planner:verified"]
    assert result.requested_at.tzinfo is not None


def test_design_run_rejects_recommendation_for_page_missing_from_plan() -> None:
    plan = sample_plan()
    recommendation = ComponentRecommendation(
        page_ids=["ghost"],
        recommended_sources=["Lucide"],
        page_components=[
            PageComponentRecommendation(page_id="ghost", components=["Card"], icons=[])
        ],
    )
    with pytest.raises(ValidationError, match="PagePlan page ids"):
        DesignRunResult.new(
            "needs_revision",
            ["planner:verified", "component_recommender:verified"],
            plan,
            recommendation,
            None,
            None,
            None,
        )


def test_final_review_keeps_revision_reason() -> None:
    review = FinalReview(status="needs_revision", findings=["화면 수가 기획과 다릅니다."])
    assert review.status == "needs_revision"
    assert review.findings
