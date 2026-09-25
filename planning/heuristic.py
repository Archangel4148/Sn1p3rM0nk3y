"""Greedy lookahead planner: shop toward the next unbeatable round, then StartRound.

Contract: plan() returns a complete Action tape through target_round that
survives every round at clear_margin=1.0 (true soft/hard gate), whenever that
is possible with the given tower pool and income. It must not return a
truncated "fake survive" tape.

clear_margin > 1.0 is an aspirational shopping target (over-prepare), not a
hard abort threshold.

Pick policy: upcoming typed coverage combos (camo+lead, …) and hard missing
coverage first, then status, $/progress (with place tax), survival margin, and
one-step upgrade option value. While a shopping-margin threat is open, keep
buying progress (breakpoint banking is still allowed if the round about to play
already survives). Save-on-expensive only applies after the threat already
meets the shopping margin.
"""

from __future__ import annotations

from actions import Action, PlaceTower, StartRound, Upgrade
from catalog import Catalog
from data.enums import Tower
from data.rounds_data import RoundData
from harness.simulated_harness import SimulatedHarness
from observation import GameSetup, Observation
from planning import Planner
from planning.evaluate import (
    RoundVerdict,
    RoundVerdictStatus,
    coverage_label,
    coverage_prep_urgent,
    evaluate_round,
    purchase_illegality,
    round_rbe_by_coverage,
    total_coverage_unlock_distance,
    unmet_coverage_sets,
    upcoming_coverage_sets,
)
from system_flags import vprint

# Prefer pass > soft_fail > hard_fail when ranking fork outcomes.
_STATUS_RANK = {
    RoundVerdictStatus.PASS: 0,
    RoundVerdictStatus.SOFT_FAIL: 1,
    RoundVerdictStatus.HARD_FAIL: 2,
}

# Hard survive / StartRound gate — independent of shopping clear_margin.
_SURVIVE_MARGIN = 1.0


class HeuristicPlanner(Planner):
    """Offline search on SimulatedHarness. Emits a full Action tape."""

    def __init__(
        self,
        setup: GameSetup,
        towers: list[Tower],
        *,
        target_round: int = 40,
        max_shop_actions_per_round: int = 40,
        clear_margin: float = 1.0,
        place_cost_tax: float = 1.75,
        margin_cap: float = 2.0,
        option_value_lambda: float = 0.35,
        save_cost_per_max: float = 28.0,
        breakpoint_near_gap: float = 400.0,
        save_when_near_breakpoint_cost_per: float = 12.0,
    ):
        self.setup = setup
        self.towers = towers
        self.target_round = target_round
        self.max_shop_actions_per_round = max_shop_actions_per_round
        self.clear_margin = clear_margin
        self.place_cost_tax = place_cost_tax
        self.margin_cap = margin_cap
        self.option_value_lambda = option_value_lambda
        self.save_cost_per_max = save_cost_per_max
        self.breakpoint_near_gap = breakpoint_near_gap
        self.save_when_near_breakpoint_cost_per = save_when_near_breakpoint_cost_per
        self._ref_counter = 0

    def _evaluate(self, obs: Observation, round_data: RoundData, catalog: Catalog):
        """Shopping-target evaluation (may use clear_margin > 1)."""
        return evaluate_round(
            obs, round_data, catalog, clear_margin=self.clear_margin
        )

    def _evaluate_survive(
        self, obs: Observation, round_data: RoundData, catalog: Catalog
    ):
        """True soft/hard gate used for StartRound / incomplete abort."""
        return evaluate_round(
            obs, round_data, catalog, clear_margin=_SURVIVE_MARGIN
        )

    def plan(self, observation: Observation, catalog: Catalog) -> list[Action]:
        # v1: always plan from a fresh reset of self.setup (ignore mid-match obs).
        del observation
        return self._search(catalog)

    def _next_threat(
        self, obs: Observation, catalog: Catalog
    ) -> tuple[RoundVerdict, RoundData] | None:
        """First round in [current, target] the board cannot pass."""
        for round_num in range(obs.believed.round_index, self.target_round + 1):
            round_data = catalog.rounds.get_round_data(round_num)
            if round_data is None:
                return None
            verdict = self._evaluate(obs, round_data, catalog)
            if verdict.status != RoundVerdictStatus.PASS:
                return verdict, round_data
        return None

    def _shop_toward(
        self,
        sim: SimulatedHarness,
        obs: Observation,
        catalog: Catalog,
        threat_rd: RoundData,
        verdict: RoundVerdict,
        plan: list[Action],
        *,
        allow_save: bool,
    ) -> tuple[Observation, RoundVerdict]:
        """Buy until threat passes; then unlock urgent upcoming coverage combos."""
        pool = tuple(self.towers)
        for _ in range(self.max_shop_actions_per_round):
            needed = upcoming_coverage_sets(
                catalog, obs.believed.round_index, self.target_round
            )
            unmet = unmet_coverage_sets(obs.believed.placed, catalog, needed)
            unlock = total_coverage_unlock_distance(
                obs.believed.placed, catalog, needed, tower_pool=pool
            )
            prep = coverage_prep_urgent(
                catalog,
                unmet,
                current_round=obs.believed.round_index,
                target_round=self.target_round,
                unlock_distance=unlock,
            )
            if verdict.status == RoundVerdictStatus.PASS and not prep:
                break
            candidates = self._candidate_actions(sim, obs, catalog)
            pick = self._pick_action(
                sim,
                obs,
                catalog,
                threat_rd,
                verdict,
                candidates,
                allow_save=allow_save,
                coverage_urgent=prep,
            )
            if pick is None:
                if unmet and prep:
                    vprint(
                        f"[plan] coverage still unmet "
                        f"({', '.join(coverage_label(r) for r in unmet)}); "
                        f"cash=${obs.believed.cash:.0f}"
                    )
                elif allow_save:
                    vprint(
                        f"[plan] save "
                        f"(cash=${obs.believed.cash:.0f}, "
                        f"budget={verdict.damage_budget:.0f}/"
                        f"{verdict.rbe * self.clear_margin:.0f})"
                    )
                else:
                    vprint(
                        f"[plan] no improving buy "
                        f"(cash=${obs.believed.cash:.0f}, "
                        f"budget={verdict.damage_budget:.0f}/"
                        f"{verdict.rbe * self.clear_margin:.0f})"
                    )
                break
            result = sim.step(pick)
            obs = result.observation
            if not result.ok:
                raise RuntimeError(f"planner step failed: {result.error}")
            plan.append(pick)
            verdict = self._evaluate(obs, threat_rd, catalog)
            needed = upcoming_coverage_sets(
                catalog, obs.believed.round_index, self.target_round
            )
            unmet = unmet_coverage_sets(obs.believed.placed, catalog, needed)
            unlock = total_coverage_unlock_distance(
                obs.believed.placed, catalog, needed, tower_pool=pool
            )
            prep = coverage_prep_urgent(
                catalog,
                unmet,
                current_round=obs.believed.round_index,
                target_round=self.target_round,
                unlock_distance=unlock,
            )
            if verdict.status == RoundVerdictStatus.PASS and not prep:
                vprint(
                    f"[plan] cleared threat r{threat_rd.round_num} "
                    f"(budget={verdict.damage_budget:.0f}/"
                    f"{verdict.rbe * self.clear_margin:.0f})"
                )
                break
            if verdict.status == RoundVerdictStatus.PASS and prep:
                vprint(
                    f"[plan] threat r{threat_rd.round_num} ok; "
                    f"unlocking coverage ({unlock:.0f} steps left)"
                )
        return obs, verdict

    def _search(self, catalog: Catalog) -> list[Action]:
        sim = SimulatedHarness()
        sim._catalog = catalog
        obs = sim.reset(self.setup)
        plan: list[Action] = []

        while obs.believed.round_index <= self.target_round:
            current = obs.believed.round_index
            current_rd = catalog.rounds.get_round_data(current)
            if current_rd is None:
                raise RuntimeError(f"no round data for {current}")

            threat = self._next_threat(obs, catalog)
            needed = upcoming_coverage_sets(catalog, current, self.target_round)
            unmet = unmet_coverage_sets(obs.believed.placed, catalog, needed)
            unlock = total_coverage_unlock_distance(
                obs.believed.placed, catalog, needed, tower_pool=tuple(self.towers)
            )
            prep = coverage_prep_urgent(
                catalog,
                unmet,
                current_round=current,
                target_round=self.target_round,
                unlock_distance=unlock,
            )

            if threat is None and not prep:
                vprint(
                    f"[plan] clear through r{self.target_round} "
                    f"(at r{current}, cash=${obs.believed.cash:.0f}); start"
                )
            else:
                if threat is None:
                    # DPS clear, but an urgent future combo still needs unlock.
                    threat_rd = None
                    for round_num in range(current, self.target_round + 1):
                        rd = catalog.rounds.get_round_data(round_num)
                        if rd is None:
                            continue
                        buckets = {
                            req
                            for req, rbe in round_rbe_by_coverage(rd).items()
                            if req in unmet and rbe > 1e-9
                        }
                        if buckets:
                            threat_rd = rd
                            break
                    if threat_rd is None:
                        threat_rd = current_rd
                    verdict = self._evaluate(obs, threat_rd, catalog)
                    vprint(
                        f"[plan] r{current} coverage prep "
                        f"({', '.join(coverage_label(r) for r in unmet)}; "
                        f"cash=${obs.believed.cash:.0f})"
                    )
                else:
                    verdict, threat_rd = threat
                    ahead = threat_rd.round_num - current
                    required = verdict.rbe * self.clear_margin
                    where = (
                        "upcoming"
                        if ahead == 0
                        else f"lookahead +{ahead} (r{threat_rd.round_num})"
                    )
                    vprint(
                        f"[plan] r{current} threat={where} {verdict.status.value} "
                        f"(cash=${obs.believed.cash:.0f}, "
                        f"budget={verdict.damage_budget:.0f}/{required:.0f})"
                    )
                    if unmet and prep:
                        vprint(
                            f"[plan]   urgent coverage: "
                            f"{', '.join(coverage_label(r) for r in unmet)}"
                        )

                current_ok = (
                    self._evaluate_survive(obs, current_rd, catalog).status
                    == RoundVerdictStatus.PASS
                )
                obs, verdict = self._shop_toward(
                    sim,
                    obs,
                    catalog,
                    threat_rd,
                    verdict,
                    plan,
                    allow_save=current_ok,
                )

                now = self._evaluate_survive(obs, current_rd, catalog)
                if now.status != RoundVerdictStatus.PASS:
                    raise RuntimeError(
                        f"cannot clear r{now.round_num} with available towers/"
                        f"cash ({now.status.value}, "
                        f"budget={now.damage_budget:.0f}/{now.rbe:.0f}, "
                        f"cash=${obs.believed.cash:.0f}). "
                        f"Partial plans are not returned."
                    )

            start = StartRound()
            result = sim.step(start)
            obs = result.observation
            if not result.ok:
                raise RuntimeError(f"StartRound failed: {result.error}")
            plan.append(start)

        if obs.believed.round_index <= self.target_round:
            raise RuntimeError(
                f"plan incomplete: ended at r{obs.believed.round_index}, "
                f"target was {self.target_round}"
            )
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

    def _survival_margin(self, verdict: RoundVerdict) -> float:
        required = max(verdict.rbe * self.clear_margin, 1e-6)
        raw = verdict.damage_budget / required
        return min(raw, self.margin_cap)

    def _followup_option_value(
        self,
        sim_after: SimulatedHarness,
        obs_after: Observation,
        catalog: Catalog,
        threat_rd: RoundData,
        after: RoundVerdict,
    ) -> float:
        """Best affordable next-upgrade efficiency (progress per dollar) after A."""
        required = after.rbe * self.clear_margin
        deficit = max(0.0, required - after.damage_budget)
        best = 0.0

        for placed in obs_after.believed.placed:
            if not isinstance(placed.tower, Tower):
                continue
            for path in catalog.legal_upgrades(placed):
                action = Upgrade(ref=placed.ref, upgrade_path=path)
                if purchase_illegality(obs_after, self.setup, action, catalog) is not None:
                    continue
                cost = catalog.cost_upgrade(
                    placed, action.upgrade_path, self.setup.difficulty
                )
                if cost <= 0 or obs_after.believed.cash < cost:
                    continue
                fork = sim_after.clone()
                result = fork.step(action)
                if not result.ok:
                    continue
                nxt = self._evaluate(result.observation, threat_rd, catalog)
                delta = nxt.damage_budget - after.damage_budget
                progress = min(delta, deficit) if deficit > 1e-6 else max(delta, 0.0)
                if progress <= 1e-6:
                    if _STATUS_RANK[nxt.status] < _STATUS_RANK[after.status]:
                        best = max(best, 1.0 / cost)
                    continue
                best = max(best, progress / cost)
        return best

    def _near_upgrade_breakpoint(self, obs: Observation, catalog: Catalog) -> bool:
        """True if some legal upgrade is just out of reach (worth banking)."""
        cash = obs.believed.cash
        for placed in obs.believed.placed:
            if not isinstance(placed.tower, Tower):
                continue
            for path in catalog.legal_upgrades(placed):
                cost = catalog.cost_upgrade(
                    placed, path, self.setup.difficulty
                )
                gap = cost - cash
                if 0 < gap <= self.breakpoint_near_gap:
                    return True
        return False

    def _pick_action(
        self,
        sim: SimulatedHarness,
        obs: Observation,
        catalog: Catalog,
        threat_rd: RoundData,
        before: RoundVerdict,
        candidates: list[Action],
        *,
        allow_save: bool = True,
        coverage_urgent: bool = False,
    ) -> Action | None:
        """Choose one shop action scored against the lookahead threat round.

        Rank: upcoming unmet coverage combos (when urgent), hard missing, status,
        $/progress, place penalty, survival margin, follow-up upgrade value.
        Returns None to Save (or no improving buy).
        """
        if not candidates:
            return None

        needed = upcoming_coverage_sets(
            catalog, obs.believed.round_index, self.target_round
        )
        pool = tuple(self.towers)
        if coverage_urgent:
            before_unmet = unmet_coverage_sets(obs.believed.placed, catalog, needed)
            before_unlock = total_coverage_unlock_distance(
                obs.believed.placed, catalog, needed, tower_pool=pool
            )
        else:
            before_unmet = ()
            before_unlock = 0.0

        required = before.rbe * self.clear_margin
        deficit = max(0.0, required - before.damage_budget)

        best: Action | None = None
        best_key: tuple = ()
        best_cost_per = float("inf")
        best_progress = 0.0
        best_fixes_hard = False
        best_unlocks = False
        best_improves_status = False
        for action in candidates:
            fork = sim.clone()
            result = fork.step(action)
            if not result.ok:
                continue
            after_obs = result.observation
            after = self._evaluate(after_obs, threat_rd, catalog)
            if coverage_urgent:
                after_unmet = unmet_coverage_sets(
                    after_obs.believed.placed, catalog, needed
                )
                after_unlock = total_coverage_unlock_distance(
                    after_obs.believed.placed, catalog, needed, tower_pool=pool
                )
            else:
                after_unmet = ()
                after_unlock = 0.0
            cost = self._action_cost(obs, action, catalog)
            taxed = (
                cost * self.place_cost_tax
                if isinstance(action, PlaceTower)
                else cost
            )
            delta = after.damage_budget - before.damage_budget
            progress = min(delta, deficit) if deficit > 1e-6 else max(delta, 0.0)
            cost_per = taxed / progress if progress > 1e-6 else float("inf")
            place_penalty = 0 if isinstance(action, Upgrade) else 1
            margin = self._survival_margin(after)
            option = self._followup_option_value(
                fork, after_obs, catalog, threat_rd, after
            )
            if option > 0 and cost_per < float("inf"):
                cost_per = cost_per / (1.0 + self.option_value_lambda * option)

            completes_combo = len(after_unmet) < len(before_unmet)
            unlock_progress = after_unlock < before_unlock

            # Clear hard gaps / reach PASS first. While only soft-failing, also
            # finish upcoming coverage combos (e.g. Flash Bomb for Camo+Lead)
            # before dumping cash into marginal DPS.
            if before.status == RoundVerdictStatus.HARD_FAIL:
                key = (
                    _STATUS_RANK[after.status],
                    len(after.missing),
                    cost_per,
                    len(after_unmet),
                    after_unlock,
                    place_penalty,
                    -margin,
                    -option,
                    -progress,
                    taxed,
                )
            elif before.status == RoundVerdictStatus.SOFT_FAIL:
                imminent = threat_rd.round_num <= obs.believed.round_index + 2
                if imminent:
                    # Don't let Flash Bomb prep starve the round about to play.
                    key = (
                        _STATUS_RANK[after.status],
                        len(after.missing),
                        cost_per,
                        0 if completes_combo else 1,
                        after_unlock,
                        place_penalty,
                        -margin,
                        -option,
                        -progress,
                        taxed,
                    )
                else:
                    key = (
                        _STATUS_RANK[after.status],
                        len(after.missing),
                        0 if completes_combo else 1,
                        0 if unlock_progress else 1,
                        after_unlock,
                        cost_per,
                        place_penalty,
                        -margin,
                        -option,
                        -progress,
                        taxed,
                    )
            else:
                key = (
                    len(after_unmet),
                    after_unlock,
                    _STATUS_RANK[after.status],
                    len(after.missing),
                    cost_per,
                    place_penalty,
                    -margin,
                    -option,
                    -progress,
                    taxed,
                )
            if best is None or key < best_key:
                best = action
                best_key = key
                best_cost_per = cost_per
                best_progress = progress
                best_fixes_hard = len(after.missing) < len(before.missing)
                best_unlocks = completes_combo or unlock_progress
                best_improves_status = (
                    _STATUS_RANK[after.status] < _STATUS_RANK[before.status]
                )

        if best is None:
            return None

        if best_fixes_hard or best_improves_status:
            return best
        # Finish / advance coverage combos even while soft-failing a threat.
        if best_unlocks:
            return best

        threat_open = before.status != RoundVerdictStatus.PASS
        near_break = self._near_upgrade_breakpoint(obs, catalog)

        if threat_open or before_unmet:
            if (
                allow_save
                and near_break
                and best_cost_per > self.save_when_near_breakpoint_cost_per
                and not before_unmet
            ):
                return None
            if best_progress > 1e-6 or best_cost_per < float("inf"):
                return best
            return None

        # Threat already meets shopping margin — optional extras / Save.
        if best_cost_per > self.save_cost_per_max:
            return None

        if near_break and best_cost_per > self.save_when_near_breakpoint_cost_per:
            return None

        return best

    def _next_ref(self, tower: Tower) -> str:
        self._ref_counter += 1
        slug = tower.value.lower().replace(" ", "_")
        return f"{slug}_{self._ref_counter}"
