import pytest
from pydantic import ValidationError

from app.agents.component_recommender import recommend_components
from app.schemas.contracts import (
    ComponentRecommendation,
    PageComponentRecommendation,
    PageDefinition,
    PagePlan,
)


@pytest.fixture
def plan() -> PagePlan:
    return PagePlan(
        project_name="예약 서비스",
        page_count=4,
        pages=[
            PageDefinition(
                page_id="search",
                name="여행 검색",
                purpose="여행 상품을 찾는다",
                primary_action="검색 실행",
                required_ui=["검색창", "필터", "결과 카드"],
            ),
            PageDefinition(
                page_id="detail",
                name="상품 상세",
                purpose="상품 정보를 확인한다",
                primary_action="예약 요청",
                required_ui=["상품 정보", "예약 버튼"],
            ),
            PageDefinition(
                page_id="complete",
                name="예약 완료",
                purpose="요청 결과를 확인한다",
                primary_action="목록으로 이동",
                required_ui=["완료 안내"],
            ),
            PageDefinition(
                page_id="profile",
                name="사용자 정보",
                purpose="사용자 정보를 확인한다",
                primary_action="저장",
                required_ui=["정보 카드"],
            ),
        ],
        user_flow=["search", "detail", "complete", "profile"],
        shared_components=["Header", "PrimaryButton"],
    )


def test_search_page_gets_search_component_and_icon(plan: PagePlan) -> None:
    result = recommend_components(plan)
    search = next(item for item in result.page_components if item.page_id == "search")

    assert "SearchInput" in search.components
    assert "Search" in search.icons
    assert result.recommended_sources == ["shadcn/ui", "Lucide"]


def test_known_page_types_get_deterministic_recommendations(plan: PagePlan) -> None:
    result = recommend_components(plan)
    by_page = {item.page_id: item for item in result.page_components}

    assert by_page["detail"].components == ["Card", "Tabs", "PrimaryButton"]
    assert by_page["detail"].icons == ["MapPin", "ChevronRight"]
    assert by_page["complete"].components == ["SuccessPanel", "PrimaryButton"]
    assert by_page["complete"].icons == ["CircleCheck"]


def test_unknown_page_type_gets_safe_default_and_preserves_shared_components(
    plan: PagePlan,
) -> None:
    result = recommend_components(plan)
    profile = next(item for item in result.page_components if item.page_id == "profile")

    assert profile.components == ["Card", "PrimaryButton"]
    assert profile.icons == ["Circle"]
    assert result.shared_components == plan.shared_components
    assert result.page_ids == [page.page_id for page in plan.pages]
    assert result.license_review_required is True
    assert profile.accessibility_notes


def test_unknown_component_page_is_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown page"):
        ComponentRecommendation(
            page_ids=["search"],
            recommended_sources=["shadcn/ui", "Lucide"],
            page_components=[
                PageComponentRecommendation(
                    page_id="missing", components=["Card"], icons=[]
                )
            ],
        )
