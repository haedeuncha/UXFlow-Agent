"""Behavioral tests for the individual UXFlow agents."""

import pytest

from app.agents.component_recommender import recommend_components
from app.agents.figma_builder import build_figma
from app.agents.final_reviewer import final_review
from app.agents.planner import create_page_plan
from app.agents.ux_reviewer import review_usability
from app.orchestration.design_flow import get_run, run_design_flow
from app.schemas.contracts import (
    ComponentRecommendation,
    DesignRequest,
    FigmaBuildResult,
    PageComponentRecommendation,
    PageDefinition,
    PagePlan,
    UsabilityChecks,
    UsabilityReview,
)


@pytest.fixture
def plan_without_completion() -> PagePlan:
    return PagePlan(
        project_name="예약 서비스",
        page_count=1,
        pages=[
            PageDefinition(
                page_id="search",
                name="검색",
                purpose="3회 이내 클릭 목표: 예약 상품을 찾는다",
                primary_action="검색 실행",
                required_ui=["검색창"],
            )
        ],
        user_flow=["search"],
        shared_components=["Header", "ErrorMessage", "ResponsiveLayout"],
    )


def test_low_score_review_has_concrete_finding(plan_without_completion: PagePlan) -> None:
    recommendation = recommend_components(plan_without_completion)

    review = review_usability(plan_without_completion, recommendation)

    assert review.passed is False
    assert review.score < 5
    assert review.findings == ["완료 화면과 완료 피드백이 필요합니다."]
    assert review.checks.completion_feedback is False


def test_plan_only_never_creates_figma_url(plan_without_completion: PagePlan) -> None:
    result = build_figma(plan_without_completion, mode="plan_only")

    assert result.status == "skipped"
    assert result.figma_url is None
    assert result.created_screen_count == 0
    assert result.created_page_ids == []


def test_build_mode_without_connection_preserves_error(plan_without_completion: PagePlan) -> None:
    result = build_figma(plan_without_completion, mode="build_figma")

    assert result.status == "failed"
    assert result.error_code == "figma_not_connected"
    assert result.figma_url is None
    assert result.created_screen_count == 0


def sample_request(features: list[str] | None = None) -> DesignRequest:
    return DesignRequest(
        service_name="여행 예약 서비스",
        target_users=["여행자"],
        primary_user_goal="예약 요청 완료",
        required_features=features or ["검색", "상세 보기", "예약 요청"],
        platforms=["web", "mobile"],
    )


def test_planner_makes_one_page_per_feature_and_completion_page() -> None:
    plan = create_page_plan(sample_request())

    assert plan.project_name == "여행 예약 서비스"
    assert plan.page_count == 4
    assert [page.page_id for page in plan.pages] == ["search", "detail", "booking", "complete"]
    assert plan.user_flow == ["search", "detail", "booking", "complete"]
    assert "예약 요청 완료" in plan.pages[-1].purpose
    assert "3회 이내 클릭" in plan.pages[-1].purpose
    assert "ErrorMessage" in plan.shared_components
    assert "ResponsiveLayout" in plan.shared_components


def test_planner_uses_distinct_ids_for_unrecognized_features() -> None:
    plan = create_page_plan(sample_request(["상품 비교", "찜 목록"]))

    assert plan.page_count == 3
    assert len({page.page_id for page in plan.pages}) == 3
    assert plan.user_flow[-1] == "complete"


def test_planner_rejects_more_features_than_page_contract_allows() -> None:
    request = sample_request([f"기능 {number}" for number in range(30)])

    with pytest.raises(ValueError, match="29"):
        create_page_plan(request)


def test_reviewer_passes_complete_short_plan() -> None:
    plan = create_page_plan(sample_request())

    review = review_usability(plan, recommend_components(plan))

    assert review.passed is True
    assert review.score == 5
    assert review.findings == []
    assert all(review.checks.model_dump().values())


def test_reviewer_flags_missing_error_and_mobile_guidance() -> None:
    plan = create_page_plan(sample_request(["검색"]))
    plan = plan.model_copy(update={"shared_components": ["Header"]})

    review = review_usability(plan, recommend_components(plan))

    assert review.passed is False
    assert review.checks.error_guidance is False
    assert review.checks.responsive_design is False
    assert len(review.findings) == 2


def test_reviewer_flags_flow_longer_than_three_clicks() -> None:
    plan = create_page_plan(sample_request(["검색", "상세 보기", "예약 요청", "결제 확인"]))

    review = review_usability(plan, recommend_components(plan))

    assert review.passed is False
    assert review.checks.three_click_goal is False
    assert any("3회" in finding for finding in review.findings)


def test_reviewer_requires_explicit_three_click_goal_statement() -> None:
    plan = create_page_plan(sample_request(["검색"]))
    plan.pages[-1].purpose = "결과를 확인한다"

    review = review_usability(plan, recommend_components(plan))

    assert review.passed is False
    assert review.checks.three_click_goal is False


def test_reviewer_flags_placeholder_action_label() -> None:
    plan = create_page_plan(sample_request(["검색"]))
    plan.pages[0].primary_action = "TODO"

    review = review_usability(plan, recommend_components(plan))

    assert review.passed is False
    assert review.checks.plain_language is False


def test_reviewer_rejects_recommendations_for_a_different_plan() -> None:
    plan = create_page_plan(sample_request(["검색"]))
    unrelated = ComponentRecommendation(
        page_ids=["other"],
        recommended_sources=["Lucide"],
        page_components=[
            PageComponentRecommendation(page_id="other", components=["Card"], icons=[])
        ],
    )

    with pytest.raises(ValueError, match="recommendation page ids"):
        review_usability(plan, unrelated)


def test_final_reviewer_rejects_screen_count_mismatch() -> None:
    plan = create_page_plan(sample_request(["검색"]))
    build = FigmaBuildResult(
        status="completed",
        figma_url="https://www.figma.com/design/abc",
        created_screen_count=1,
        created_page_ids=["search"],
    )

    result = final_review(plan, build)

    assert result.status == "needs_revision"
    assert any("화면 수" in finding for finding in result.findings)


def test_final_reviewer_rejects_wrong_page_ids_even_with_matching_count() -> None:
    plan = create_page_plan(sample_request(["검색"]))
    build = FigmaBuildResult(
        status="completed",
        figma_url="https://www.figma.com/design/abc",
        created_screen_count=2,
        created_page_ids=["search", "unknown"],
    )

    result = final_review(plan, build)

    assert result.status == "needs_revision"
    assert any("페이지" in finding for finding in result.findings)


def test_final_reviewer_accepts_matching_completed_build() -> None:
    plan = create_page_plan(sample_request(["검색"]))
    build = FigmaBuildResult(
        status="completed",
        figma_url="https://www.figma.com/design/abc",
        created_screen_count=2,
        created_page_ids=["search", "complete"],
    )

    result = final_review(plan, build)

    assert result.status == "completed"
    assert result.findings == []


def test_final_reviewer_preserves_failed_build_reason() -> None:
    plan = create_page_plan(sample_request(["검색"]))

    result = final_review(plan, build_figma(plan, mode="build_figma"))

    assert result.status == "failed"
    assert any("figma_not_connected" in finding for finding in result.findings)


def test_failed_usability_review_skips_figma_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_review(*_: object) -> UsabilityReview:
        return UsabilityReview(
            passed=False,
            score=4,
            findings=["보완이 필요합니다."],
            checks=UsabilityChecks(),
        )

    monkeypatch.setattr(
        "app.orchestration.design_flow.review_usability", failing_review
    )

    result = run_design_flow(sample_request(), mode="build_figma")

    assert result.status == "needs_revision"
    assert "ux_reviewer:needs_revision" in result.trace
    assert "figma_builder:skipped" in result.trace
    assert result.build is None


def test_completed_plan_only_run_is_retrievable() -> None:
    result = run_design_flow(sample_request(), mode="plan_only")

    assert result.status == "completed"
    assert result.build is not None
    assert result.build.status == "skipped"
    assert "figma_builder:skipped" in result.trace
    assert get_run(result.run_id) == result


def test_build_mode_preserves_missing_figma_connection_failure() -> None:
    result = run_design_flow(sample_request(), mode="build_figma")

    assert result.status == "failed"
    assert result.build is not None
    assert result.build.error_code == "figma_not_connected"
    assert "figma_builder:failed:figma_not_connected" in result.trace
