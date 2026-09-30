"""Deterministic usability checks over a validated page plan."""

from app.schemas.contracts import (
    ComponentRecommendation,
    PagePlan,
    UsabilityChecks,
    UsabilityReview,
)


def review_usability(
    plan: PagePlan, recommendation: ComponentRecommendation
) -> UsabilityReview:
    """Require a clear, short flow with error and completion guidance."""
    page_ids = {page.page_id for page in plan.pages}
    recommended_ids = {item.page_id for item in recommendation.page_components}
    if set(recommendation.page_ids) != page_ids or recommended_ids != page_ids:
        raise ValueError("추천 결과의 페이지 ID는 화면 계획의 페이지 ID와 같아야 합니다.")

    complete_pages = [page for page in plan.pages if page.page_id == "complete"]
    completion_feedback = bool(
        complete_pages
        and plan.user_flow[-1] == "complete"
        and any("완료" in item or "success" in item.lower() for item in complete_pages[0].required_ui)
    )
    checks = UsabilityChecks(
        clear_primary_action=all(page.primary_action.strip() for page in plan.pages),
        three_click_goal=(
            len(plan.user_flow) - 1 <= 3
            and any("3회 이내 클릭" in page.purpose for page in plan.pages)
        ),
        plain_language=all(
            _plain_label(page.name) and _plain_label(page.primary_action)
            for page in plan.pages
        ),
        error_guidance="ErrorMessage" in plan.shared_components,
        responsive_design="ResponsiveLayout" in plan.shared_components,
        completion_feedback=completion_feedback,
    )
    findings = []
    if not checks.clear_primary_action:
        findings.append("모든 화면에 핵심 행동을 명확히 표시해야 합니다.")
    if not checks.three_click_goal:
        findings.append("핵심 목표를 3회 이내 클릭으로 완료할 수 있도록 흐름을 줄여야 합니다.")
    if not checks.plain_language:
        findings.append("화면 이름과 행동 문구를 쉬운 말로 작성해야 합니다.")
    if not checks.error_guidance:
        findings.append("오류 발생 시 사용자가 다음 행동을 알 수 있는 안내가 필요합니다.")
    if not checks.responsive_design:
        findings.append("모바일 화면을 고려한 반응형 구성이 필요합니다.")
    if not checks.completion_feedback:
        findings.append("완료 화면과 완료 피드백이 필요합니다.")
    return UsabilityReview(
        passed=not findings,
        score=max(1, 5 - len(findings)),
        findings=findings,
        checks=checks,
    )


def _plain_label(label: str) -> bool:
    normalized = label.casefold()
    return "_" not in label and not any(
        placeholder in normalized for placeholder in ("todo", "tbd", "lorem")
    )
