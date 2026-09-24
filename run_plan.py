"""Build a plan with a Planner, then evaluate it on SimulatedHarness.

Edit the constants below to swap planners / target round / plan dump.
Register new planners in PLANNERS.
"""

from __future__ import annotations

from collections.abc import Callable

from actions import Action
from catalog import Catalog
from data.enums import Tower
from harness.simulated_harness import SimulatedHarness
from observation import GameSetup
from plans.meadow_smoke import SETUP
from planning import Planner
from planning.evaluate import evaluate_plan
from planning.heuristic import HeuristicPlanner
from system_flags import vprint

# --- knobs ---
PLANNER = "heuristic"
TARGET_ROUND = 40
SHOW_PLAN = True
# Must match for plan + eval. >1.0 = over-prepare for the soft gate.
CLEAR_MARGIN = 1.5

# Default tower pool for search-style planners (no heroes).
DEFAULT_TOWERS = [
    Tower.DART_MONKEY,
    Tower.NINJA_MONKEY,
    Tower.BOMB_SHOOTER,
]


def make_heuristic(setup: GameSetup, target_round: int) -> Planner:
    return HeuristicPlanner(
        setup,
        DEFAULT_TOWERS,
        target_round=target_round,
        clear_margin=CLEAR_MARGIN,
        max_shop_actions_per_round=20
    )


PLANNERS: dict[str, Callable[[GameSetup, int], Planner]] = {
    "heuristic": make_heuristic,
}


def summarize_plan(plan: list[Action], *, show_actions: bool) -> None:
    counts: dict[str, int] = {}
    for action in plan:
        name = type(action).__name__
        counts[name] = counts.get(name, 0) + 1
    vprint(f"Plan length {len(plan)}: {counts}")
    if show_actions:
        for i, action in enumerate(plan):
            vprint(f"  {i:3d}  {action}")


def print_evaluation(report) -> None:
    if report.illegal_purchase:
        summary = f"Plan ILLEGAL ({report.illegal_purchase})"
    elif report.ok:
        summary = "Plan estimated SURVIVE"
    else:
        summary = "Plan estimated LOSE"
        if report.first_loss_round is not None:
            summary += f" (first loss round {report.first_loss_round})"
    if report.error and not report.illegal_purchase:
        summary += f" error={report.error}"
    vprint(summary)

    for verdict in report.rounds:
        mark = "ok" if not verdict.estimated_lose else "LOSE"
        vprint(
            f"  r{verdict.round_num} [{mark}/{verdict.status.value}] "
            f"rbe={verdict.rbe} budget={verdict.damage_budget:.0f} "
            f"eff={verdict.effective_dps:.1f} {verdict.detail}"
        )


def main() -> None:
    catalog = Catalog()
    setup = SETUP
    planner = PLANNERS[PLANNER](setup, TARGET_ROUND)

    obs = SimulatedHarness().reset(setup)
    plan = planner.plan(obs, catalog)

    vprint(
        f"Planner={PLANNER} target_round={TARGET_ROUND} clear_margin={CLEAR_MARGIN}"
    )
    summarize_plan(plan, show_actions=SHOW_PLAN)
    print_evaluation(
        evaluate_plan(setup, plan, catalog=catalog, clear_margin=CLEAR_MARGIN)
    )


if __name__ == "__main__":
    main()
