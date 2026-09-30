"""In-memory persistence for observable UXFlow runs.

Stored results intentionally live only for the lifetime of this Python process.
"""

from app.schemas.contracts import DesignRunResult


_runs: dict[str, DesignRunResult] = {}


def save_run(result: DesignRunResult) -> DesignRunResult:
    """Persist one validated result and return the same object for handoff."""
    _runs[result.run_id] = result
    return result


def get_run(run_id: str) -> DesignRunResult | None:
    """Return a previous run when it is still in this process's memory."""
    return _runs.get(run_id)
