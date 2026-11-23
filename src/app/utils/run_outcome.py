"""How a hydration run ended, read from the backend's provenance sidecar.

The backend writes ``Result/run_metadata.json`` when a run starts
(``exit_reason == "in_progress"``) and rewrites it when the run stops. That
file, not the process exit code, is the authority on whether a run succeeded:
older backends exited 0 after recording a failure (fixed in 6.0.1), and a run
can also end early at a physical endpoint, which is a success that did not
reach the requested final time.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

ENDED_EARLY_PREFIX = "Simulation ended early"


@dataclass
class RunOutcome:
    finalized: bool          # False while the run is still in progress
    success: bool
    exit_code: Optional[int]
    exit_reason: str
    diagnostics: str
    backend_version: str = ""
    backend_git_hash: str = ""
    ui_version: str = ""

    @property
    def failed(self) -> bool:
        return self.finalized and not self.success

    @property
    def ended_early(self) -> bool:
        return self.finalized and self.success and self.exit_reason.startswith(ENDED_EARLY_PREFIX)


def read_run_outcome(operation_dir) -> Optional[RunOutcome]:
    """Return the run's outcome, or None if there is no readable sidecar."""
    path = Path(operation_dir) / "Result" / "run_metadata.json"
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    run = data.get("run", {}) or {}
    backend = data.get("thames_backend", {}) or {}
    ui = data.get("thames_ui", {}) or {}
    reason = str(run.get("exit_reason") or "unknown")
    exit_code = run.get("exit_code")
    finalized = reason != "in_progress"
    success = bool(run.get("success", exit_code == 0))
    return RunOutcome(
        finalized=finalized,
        success=success,
        exit_code=exit_code,
        exit_reason=reason,
        diagnostics=str(run.get("diagnostics") or ""),
        backend_version=str(backend.get("version") or ""),
        backend_git_hash=str(backend.get("git_hash") or ""),
        ui_version=str(ui.get("version") or ""),
    )


def read_time_reached(operation_dir) -> Optional[Tuple[float, Optional[float]]]:
    """(time reached, target time) in hours from progress.json, if present."""
    path = Path(operation_dir) / "progress.json"
    try:
        with open(path, "r") as f:
            data = json.load(f)
        reached = float(data.get("time_hours"))
    except (OSError, ValueError, TypeError):
        return None
    target = data.get("target_time_hours")
    try:
        target = float(target) if target is not None else None
    except (TypeError, ValueError):
        target = None
    return reached, target


def _format_hours(hours: float) -> str:
    if hours >= 24.0:
        return f"{hours / 24.0:.2f} d"
    return f"{hours:.2f} h"


def outcome_step_text(outcome: RunOutcome, operation_dir) -> Optional[str]:
    """Current Step text for a finished run that did not simply complete."""
    times = read_time_reached(operation_dir)
    where = ""
    if times is not None:
        reached, target = times
        where = f" at {_format_hours(reached)}"
        if target:
            where += f" of {_format_hours(target)}"
    if outcome.failed:
        return f"FAILED{where}: {outcome.exit_reason}"
    if outcome.ended_early:
        detail = outcome.exit_reason[len(ENDED_EARLY_PREFIX):].lstrip(" :")
        return f"Completed: ended early{where}" + (f" ({detail})" if detail else "")
    return None


def progress_fraction(operation_dir) -> Optional[float]:
    """Fraction of the requested time reached, from progress.json."""
    times = read_time_reached(operation_dir)
    if times is None or not times[1]:
        return None
    reached, target = times
    return max(0.0, min(1.0, reached / target))
