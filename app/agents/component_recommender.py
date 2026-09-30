"""Recommend a small, safe set of UI components and icons per planned page."""

from app.schemas.contracts import (
    ComponentRecommendation,
    PageComponentRecommendation,
    PagePlan,
)


KEYWORD_RULES: dict[str, tuple[list[str], list[str]]] = {
    "search": (
        ["SearchInput", "FilterSheet", "ResultCard"],
        ["Search", "SlidersHorizontal"],
    ),
    "detail": (["Card", "Tabs", "PrimaryButton"], ["MapPin", "ChevronRight"]),
    "complete": (["SuccessPanel", "PrimaryButton"], ["CircleCheck"]),
}

DEFAULT_RECOMMENDATION = (["Card", "PrimaryButton"], ["Circle"])
ACCESSIBILITY_NOTE = "모든 아이콘 버튼에는 접근 가능한 이름을 제공한다."


def recommend_components(plan: PagePlan) -> ComponentRecommendation:
    """Create validated recommendations without fetching external assets."""
    page_components = []
    for page in plan.pages:
        components, icons = KEYWORD_RULES.get(page.page_id, DEFAULT_RECOMMENDATION)
        page_components.append(
            PageComponentRecommendation(
                page_id=page.page_id,
                components=components,
                icons=icons,
                accessibility_notes=[ACCESSIBILITY_NOTE],
            )
        )

    return ComponentRecommendation(
        page_ids=[page.page_id for page in plan.pages],
        recommended_sources=["shadcn/ui", "Lucide"],
        page_components=page_components,
        shared_components=plan.shared_components,
        license_review_required=True,
    )
