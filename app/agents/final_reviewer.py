"""Compare reported Figma output with the approved page plan."""

from app.schemas.contracts import FigmaBuildResult, FinalReview, PagePlan


def final_review(plan: PagePlan, build: FigmaBuildResult) -> FinalReview:
    """Only accept a completed build with every planned screen in order."""
    if build.status != "completed":
        reason = build.error_code or build.error or "Figma 생성이 실행되지 않았습니다."
        return FinalReview(status="failed", findings=[reason])

    findings = []
    if build.created_screen_count != plan.page_count:
        findings.append("생성된 화면 수가 기획한 페이지 수와 다릅니다.")
    if build.created_page_ids != plan.user_flow:
        findings.append("생성된 페이지 목록과 순서가 기획한 사용자 흐름과 다릅니다.")
    return FinalReview(
        status="needs_revision" if findings else "completed",
        findings=findings,
    )
