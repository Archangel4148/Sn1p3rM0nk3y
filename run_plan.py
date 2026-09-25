"""Build a plan with a Planner, then evaluate it on SimulatedHarness.

Edit the constants below to swap planners / target round / plan dump.
Register new planners in PLANNERS.
"""

from __future__ import annotations

from collections.abc import Callable

from actions import Action
from catalog import Catalog
from data.enums import Tower, UpgradePath
from harness.simulated_harness import SimulatedHarness
from observation import GameSetup
from plans.meadow_smoke import SETUP
from planning import Planner
from planning.evaluate import evaluate_plan
from planning.goal_planner import GoalPlanner
from planning.heuristic import HeuristicPlanner
import system_flags
from system_flags import vprint

# --- knobs ---
PLANNER = "goal"
TARGET_ROUND = 60
SHOW_PLAN = True
# [plan]/[sim]/[eval] spam while searching/replaying. Summary always prints after.
SHOW_PLANNING_LOG = False
# Must match for plan shopping target. Survive / abort uses margin 1.0;
# >1.0 = over-prepare preference while shopping, not a hard fail gate.
CLEAR_MARGIN = 1.7
MAX_SHOP_ACTIONS = 5
# Multiplier on PlaceTower cost when scoring $/progress (upgrades untaxed).
PLACE_COST_TAX = 1.75
# Prefer budgets up to this multiple of required (survival margin).
MARGIN_CAP = 2.0
# Weight on one-step follow-up upgrade efficiency.
OPTION_VALUE_LAMBDA = 0.35
# Save (buy nothing) if best $/progress exceeds this — when current already passes.
SAVE_COST_PER_MAX = 28.0
# If an upgrade is within this many $ of affordability, prefer banking
# unless the best buy is cheaper than SAVE_WHEN_NEAR_BREAKPOINT_COST_PER.
BREAKPOINT_NEAR_GAP = 400.0
SAVE_WHEN_NEAR_BREAKPOINT_COST_PER = 12.0

# Default tower pool for search-style planners (no heroes).
DEFAULT_TOWERS = [
    Tower.DART_MONKEY,
    Tower.NINJA_MONKEY,
    Tower.BOMB_SHOOTER,
]


def make_goal(setup: GameSetup, target_round: int) -> Planner:
    return GoalPlanner(
        setup,
        DEFAULT_TOWERS,
        target_round=target_round,
        max_shop_actions_per_round=MAX_SHOP_ACTIONS,
    )


def make_heuristic(setup: GameSetup, target_round: int) -> Planner:
    return HeuristicPlanner(
        setup,
        DEFAULT_TOWERS,
        target_round=target_round,
        clear_margin=CLEAR_MARGIN,
        max_shop_actions_per_round=MAX_SHOP_ACTIONS,
        place_cost_tax=PLACE_COST_TAX,
        margin_cap=MARGIN_CAP,
        option_value_lambda=OPTION_VALUE_LAMBDA,
        save_cost_per_max=SAVE_COST_PER_MAX,
        breakpoint_near_gap=BREAKPOINT_NEAR_GAP,
        save_when_near_breakpoint_cost_per=SAVE_WHEN_NEAR_BREAKPOINT_COST_PER,
    )


PLANNERS: dict[str, Callable[[GameSetup, int], Planner]] = {
    "goal": make_goal,
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


def print_board(setup: GameSetup, plan: list[Action], catalog: Catalog) -> None:
    sim = SimulatedHarness()
    sim._catalog = catalog
    sim._silent = True
    obs = sim.reset(setup)
    for action in plan:
        result = sim.step(action)
        if not result.ok:
            vprint(f"Board replay stopped: {result.error}")
            return
        obs = result.observation
    paths = (UpgradePath.TOP, UpgradePath.MIDDLE, UpgradePath.BOTTOM)
    vprint("Towers:")
    for placed in obs.believed.placed:
        tiers = "-".join(str(placed.upgrades[path]) for path in paths)
        vprint(f"  {placed.ref}: {tiers} {placed.tower.value}")


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

    prev_verbose = system_flags.VERBOSE
    system_flags.VERBOSE = SHOW_PLANNING_LOG
    try:
        try:
            obs = SimulatedHarness().reset(setup)
            plan = planner.plan(obs, catalog)
        except RuntimeError as exc:
            system_flags.VERBOSE = True
            vprint(f"Planner FAILED: {exc}")
            return
        report = evaluate_plan(
            setup, plan, catalog=catalog, clear_margin=1.0
        )
    finally:
        system_flags.VERBOSE = True

    vprint(
        f"Planner={PLANNER} target_round={TARGET_ROUND} "
        f"clear_margin={CLEAR_MARGIN} place_tax={PLACE_COST_TAX} "
        f"margin_cap={MARGIN_CAP} option_lambda={OPTION_VALUE_LAMBDA} "
        f"save_cost_per_max={SAVE_COST_PER_MAX}"
    )
    summarize_plan(plan, show_actions=SHOW_PLAN)
    if len(report.rounds) < TARGET_ROUND:
        vprint(
            f"Plan INCOMPLETE: only reached r{len(report.rounds)}, "
            f"target was {TARGET_ROUND}"
        )
    print_evaluation(report)
    print_board(setup, plan, catalog)
    system_flags.VERBOSE = prev_verbose


if __name__ == "__main__":
    main()
