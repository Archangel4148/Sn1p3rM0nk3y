"""Greedy checkpoint planner: shop until the upcoming round passes, then StartRound.

Pick policy: coverage/status first, then marginal damage-budget per dollar,
with upgrades preferred on ties.
"""

from __future__ import annotations

from actions import Action, PlaceTower, StartRound, Upgrade
from catalog import Catalog
from data.enums import Tower
from harness.simulated_harness import SimulatedHarness
from observation import GameSetup, Observation
from planning import Planner
from planning.evaluate import (
    RoundVerdictStatus,
    evaluate_round,
    purchase_illegality,
)
from system_flags import vprint

# Prefer pass > soft_fail > hard_fail when ranking fork outcomes.
_STATUS_RANK = {
    RoundVerdictStatus.PASS: 0,
    RoundVerdictStatus.SOFT_FAIL: 1,
    RoundVerdictStatus.HARD_FAIL: 2,
}


class HeuristicPlanner(Planner):
    """Offline search on SimulatedHarness. Emits a full Action tape."""

    def __init__(
        self,
        setup: GameSetup,
        towers: list[Tower],
        *,
        target_round: int = 40,
        max_shop_actions_per_round: int = 6,
        clear_margin: float = 1.0,
    ):
        self.setup = setup
        self.towers = towers
        self.target_round = target_round
        self.max_shop_actions_per_round = max_shop_actions_per_round
        self.clear_margin = clear_margin
        self._ref_counter = 0

    def _evaluate(self, obs: Observation, round_data, catalog: Catalog):
        return evaluate_round(
            obs, round_data, catalog, clear_margin=self.clear_margin
        )

    def plan(self, observation: Observation, catalog: Catalog) -> list[Action]:
        # v1: always plan from a fresh reset of self.setup (ignore mid-match obs).
        del observation
        return self._search(catalog)

    def _search(self, catalog: Catalog) -> list[Action]:
        sim = SimulatedHarness()
        # Share the caller's catalog so tables aren't reloaded every plan().
        sim._catalog = catalog
        obs = sim.reset(self.setup)
        plan: list[Action] = []

        while obs.believed.round_index <= self.target_round:
            round_data = catalog.rounds.get_round_data(obs.believed.round_index)
            if round_data is None:
                vprint(f"[plan] no round data for {obs.believed.round_index}; stop")
                break

            verdict = self._evaluate(obs, round_data, catalog)
            required = verdict.rbe * self.clear_margin
            vprint(
                f"[plan] r{verdict.round_num} {verdict.status.value} "
                f"(cash=${obs.believed.cash:.0f}, "
                f"eff_dps={verdict.effective_dps:.1f}, "
                f"budget={verdict.damage_budget:.0f}/{required:.0f})"
            )

            if verdict.status != RoundVerdictStatus.PASS:
                for _ in range(self.max_shop_actions_per_round):
                    candidates = self._candidate_actions(sim, obs, catalog)
                    pick = self._pick_action(sim, obs, catalog, verdict, candidates)
                    if pick is None:
                        break
                    result = sim.step(pick)
                    obs = result.observation
                    if not result.ok:
                        vprint(f"[plan] step failed: {result.error}")
                        break
                    plan.append(pick)
                    verdict = self._evaluate(obs, round_data, catalog)
                    if verdict.status == RoundVerdictStatus.PASS:
                        break

                if verdict.status == RoundVerdictStatus.HARD_FAIL:
                    vprint(
                        f"[plan] cannot fix hard fail on r{verdict.round_num}; stop"
                    )
                    break
                if verdict.status == RoundVerdictStatus.SOFT_FAIL:
                    required = verdict.rbe * self.clear_margin
                    vprint(
                        f"[plan] still soft_fail on r{verdict.round_num} "
                        f"(budget={verdict.damage_budget:.0f}/{required:.0f}); "
                        f"starting round anyway"
                    )

            start = StartRound()
            result = sim.step(start)
            obs = result.observation
            if not result.ok:
                vprint(f"[plan] StartRound failed: {result.error}")
                break
            plan.append(start)

        return plan

    def _candidate_actions(
        self,
        sim: SimulatedHarness,
        obs: Observation,
        catalog: Catalog,
    ) -> list[Action]:
        """Legal shop actions the search is allowed to try this turn."""
        actions: list[Action] = []

        for placed in obs.believed.placed:
            if not isinstance(placed.tower, Tower):
                continue
            for path in catalog.legal_upgrades(placed):
                action = Upgrade(ref=placed.ref, upgrade_path=path)
                if purchase_illegality(obs, self.setup, action, catalog) is None:
                    actions.append(action)

        for tower in self.towers:
            cost = catalog.cost_place(tower, self.setup.difficulty)
            if obs.believed.cash < cost:
                continue
            for spot in sim.placement_candidates(tower)[:3]:
                ref = self._next_ref(tower)
                action = PlaceTower(tower=tower, position=spot.position, ref=ref)
                if purchase_illegality(obs, self.setup, action, catalog) is None:
                    actions.append(action)

        return actions

    def _action_cost(self, obs: Observation, action: Action, catalog: Catalog) -> float:
        if isinstance(action, PlaceTower):
            return catalog.cost_place(action.tower, self.setup.difficulty)
        if isinstance(action, Upgrade):
            placed = next(p for p in obs.believed.placed if p.ref == action.ref)
            return catalog.cost_upgrade(
                placed, action.upgrade_path, self.setup.difficulty
            )
        return float("inf")

    def _pick_action(
        self,
        sim: SimulatedHarness,
        obs: Observation,
        catalog: Catalog,
        before,
        candidates: list[Action],
    ) -> Action | None:
        """Choose one shop action. Fork the sim, score, keep the best.

        Rank: better verdict status, fewer missing coverages, lower $/Δbudget,
        prefer Upgrade over Place on ties, then larger budget gain.
        """
        if not candidates:
            return None

        round_data = catalog.rounds.get_round_data(obs.believed.round_index)
        if round_data is None:
            return None

        best: Action | None = None
        best_key: tuple = ()

        for action in candidates:
            fork = sim.clone()
            result = fork.step(action)
            if not result.ok:
                continue
            after = self._evaluate(result.observation, round_data, catalog)
            cost = self._action_cost(obs, action, catalog)
            delta = after.damage_budget - before.damage_budget
            cost_per = cost / delta if delta > 1e-6 else float("inf")
            place_penalty = 0 if isinstance(action, Upgrade) else 1
            key = (
                _STATUS_RANK[after.status],
                len(after.missing),
                cost_per,
                place_penalty,
                -delta,
                cost,
            )
            if best is None or key < best_key:
                best = action
                best_key = key

        return best

    def _next_ref(self, tower: Tower) -> str:
        self._ref_counter += 1
        slug = tower.value.lower().replace(" ", "_")
        return f"{slug}_{self._ref_counter}"
