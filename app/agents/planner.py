"""Turn a validated service request into a linear page plan."""

from app.schemas.contracts import DesignRequest, PageDefinition, PagePlan


def _page_id(feature: str) -> str | None:
    if "검색" in feature or "search" in feature.lower():
        return "search"
    if "상세" in feature or "detail" in feature.lower():
        return "detail"
    if "예약" in feature or "booking" in feature.lower():
        return "booking"
    return None


def _required_ui(page_id: str, feature: str) -> list[str]:
    if page_id == "search":
        return ["검색창", "결과 목록"]
    if page_id == "detail":
        return ["상세 정보", "다음 행동 버튼"]
    if page_id == "booking":
        return ["예약 요청 양식", "제출 버튼"]
    return [f"{feature} 안내", f"{feature} 버튼"]


def create_page_plan(request: DesignRequest) -> PagePlan:
    """Create one page per feature and a final completion page."""
    if len(request.required_features) > 29:
        raise ValueError("필수 기능은 완료 화면을 제외하고 최대 29개까지 지원합니다.")

    pages: list[PageDefinition] = []
    used_ids = {"complete"}
    for number, feature in enumerate(request.required_features, start=1):
        preferred_id = _page_id(feature)
        page_id = preferred_id if preferred_id and preferred_id not in used_ids else f"feature_{number}"
        used_ids.add(page_id)
        pages.append(
            PageDefinition(
                page_id=page_id,
                name=feature,
                purpose=f"{feature} 기능으로 {request.primary_user_goal} 목표를 진행한다",
                primary_action=f"{feature} 진행",
                required_ui=_required_ui(page_id, feature),
            )
        )

    pages.append(
        PageDefinition(
            page_id="complete",
            name="완료",
            purpose=f"3회 이내 클릭 목표: {request.primary_user_goal}. 결과를 확인한다",
            primary_action="처음으로 돌아가기",
            required_ui=["완료 안내", "다음 단계 안내"],
        )
    )
    return PagePlan(
        project_name=request.service_name,
        page_count=len(pages),
        pages=pages,
        user_flow=[page.page_id for page in pages],
        shared_components=[
            "Header",
            "PrimaryButton",
            "LoadingState",
            "ErrorMessage",
            "ResponsiveLayout",
        ],
    )
