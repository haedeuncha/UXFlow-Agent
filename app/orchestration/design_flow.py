"""Run UXFlow agents in their required order and preserve their trace."""

from typing import Literal

from app.agents.component_recommender import recommend_components
from app.agents.figma_builder import build_figma
from app.agents.final_reviewer import final_review
from app.agents.planner import create_page_plan
from app.agents.ux_reviewer import review_usability
from app.schemas.contracts import (
    ComponentRecommendation,
    DesignRequest,
    DesignRunResult,
    FigmaBuildResult,
    PagePlan,
    UsabilityReview,
)
from app.storage.run_store import get_run, save_run


FlowMode = Literal["plan_only", "build_figma"]


def _failed_result(
    trace: list[str],
    plan: PagePlan | None = None,
    recommendation: ComponentRecommendation | None = None,
    review: UsabilityReview | None = None,
    build: FigmaBuildResult | None = None,
) -> DesignRunResult:
    """Create a saved failure without inventing data for unfinished agents."""
    return save_run(
        DesignRunResult.new(
            "failed", trace, plan, recommendation, review, build, None
        )
    )


def run_design_flow(request: DesignRequest, mode: FlowMode) -> DesignRunResult:
    """Execute validated handoffs, stopping before every unsafe later step.

    ``plan_only`` is a successful planning workflow: it returns an explicit
    skipped Figma result and never creates a URL. ``build_figma`` preserves
    the safe adapter's honest ``figma_not_connected`` result when no explicit
    Figma integration is configured.
    """
    trace = ["planner:started"]
    try:
        plan = create_page_plan(request)
    except Exception as error:
        return _failed_result(trace + [f"planner:failed:{type(error).__name__}"])
    trace.append("planner:verified")

    try:
        recommendation = recommend_components(plan)
    except Exception as error:
        return _failed_result(
            trace + [f"component_recommender:failed:{type(error).__name__}"], plan
        )
    trace.append("component_recommender:verified")

    try:
        review = review_usability(plan, recommendation)
    except Exception as error:
        return _failed_result(
            trace + [f"ux_reviewer:failed:{type(error).__name__}"],
            plan,
            recommendation,
        )

    if not review.passed:
        return save_run(
            DesignRunResult.new(
                "needs_revision",
                trace + ["ux_reviewer:needs_revision", "figma_builder:skipped"],
                plan,
                recommendation,
                review,
                None,
                None,
            )
        )
    trace.append("ux_reviewer:verified")

    try:
        build = build_figma(plan, mode)
    except Exception as error:
        return _failed_result(
            trace + [f"figma_builder:failed:{type(error).__name__}"],
            plan,
            recommendation,
            review,
        )
    trace.append(f"figma_builder:{build.status}")

    if build.status == "failed":
        return _failed_result(trace, plan, recommendation, review, build)
    if build.status == "skipped":
        return save_run(
            DesignRunResult.new(
                "completed", trace, plan, recommendation, review, build, None
            )
        )

    try:
        final = final_review(plan, build)
    except Exception as error:
        return _failed_result(
            trace + [f"final_reviewer:failed:{type(error).__name__}"],
            plan,
            recommendation,
            review,
            build,
        )
    trace.append(f"final_reviewer:{final.status}")
    return save_run(
        DesignRunResult.new(
            final.status, trace, plan, recommendation, review, build, final
        )
    )
