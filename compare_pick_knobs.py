"""Compare heuristic pick knobs (baseline vs save/option/full)."""

from __future__ import annotations

from collections import Counter

import system_flags

system_flags.VERBOSE = False

from catalog import Catalog
from data.enums import Tower
from harness.simulated_harness import SimulatedHarness
from plans.meadow_smoke import SETUP
from planning.evaluate import RoundVerdictStatus, evaluate_plan
from planning.heuristic import HeuristicPlanner

TOWERS = [Tower.DART_MONKEY, Tower.NINJA_MONKEY, Tower.BOMB_SHOOTER]
CM = 1.5
TARGET = 40


def run(**kw):
    cat = Catalog()
    planner = HeuristicPlanner(
        SETUP,
        TOWERS,
        target_round=TARGET,
        clear_margin=CM,
        max_shop_actions_per_round=20,
        place_cost_tax=1.75,
        **kw,
    )
    plan = planner.plan(SimulatedHarness().reset(SETUP), cat)
    report = evaluate_plan(SETUP, plan, catalog=cat, clear_margin=CM)
    counts = Counter(type(a).__name__ for a in plan)
    soft = sum(1 for v in report.rounds if v.status == RoundVerdictStatus.SOFT_FAIL)
    hard = sum(1 for v in report.rounds if v.status == RoundVerdictStatus.HARD_FAIL)
    passes = sum(1 for v in report.rounds if v.status == RoundVerdictStatus.PASS)
    margins = [
        v.damage_budget / max(v.rbe * CM, 1e-6) for v in report.rounds
    ]
    sim = SimulatedHarness()
    sim._catalog = cat
    obs = sim.reset(SETUP)
    for action in plan:
        obs = sim.step(action).observation
    return {
        "ok": report.ok,
        "lose_round": report.first_loss_round,
        "len": len(plan),
        "counts": dict(counts),
        "pass": passes,
        "soft": soft,
        "hard": hard,
        "avg_margin": sum(margins) / len(margins) if margins else 0.0,
        "min_margin": min(margins) if margins else 0.0,
        "final_cash": obs.believed.cash,
        "rounds_played": len(report.rounds),
    }


def show(name: str, r: dict) -> None:
    print(f"--- {name} ---")
    print(
        f"  ok={r['ok']} lose@{r['lose_round']} "
        f"rounds={r['rounds_played']} plan_len={r['len']}"
    )
    print(f"  actions={r['counts']}")
    print(
        f"  pass/soft/hard={r['pass']}/{r['soft']}/{r['hard']} "
        f"avg_margin={r['avg_margin']:.2f} min_margin={r['min_margin']:.2f} "
        f"cash=${r['final_cash']:.0f}"
    )


def main() -> None:
    base = run(
        option_value_lambda=0.0,
        save_cost_per_max=1e9,
        save_when_near_breakpoint_cost_per=1e9,
        margin_cap=2.0,
    )
    opt_only = run(
        option_value_lambda=0.35,
        save_cost_per_max=1e9,
        save_when_near_breakpoint_cost_per=1e9,
        margin_cap=2.0,
    )
    save_only = run(
        option_value_lambda=0.0,
        save_cost_per_max=28.0,
        save_when_near_breakpoint_cost_per=12.0,
        margin_cap=2.0,
    )
    full = run(
        option_value_lambda=0.35,
        save_cost_per_max=28.0,
        save_when_near_breakpoint_cost_per=12.0,
        margin_cap=2.0,
    )
    show("baseline (margin key only; no save/option)", base)
    show("margin + option value", opt_only)
    show("margin + save", save_only)
    show("full 1+2+3", full)


if __name__ == "__main__":
    main()
