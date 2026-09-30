"""Safe Figma adapter until an explicitly connected integration exists."""

from typing import Literal

from app.schemas.contracts import FigmaBuildResult, PagePlan


def build_figma(
    plan: PagePlan, mode: Literal["plan_only", "build_figma"]
) -> FigmaBuildResult:
    """Return an honest result without creating a file or inventing a URL."""
    if mode == "plan_only":
        return FigmaBuildResult(status="skipped")
    if mode == "build_figma":
        return FigmaBuildResult(status="failed", error_code="figma_not_connected")
    raise ValueError(f"지원하지 않는 Figma 실행 모드입니다: {mode}")
