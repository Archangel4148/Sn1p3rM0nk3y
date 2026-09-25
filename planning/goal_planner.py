"""Buy a precommitted loadout forward. Survive the current round, else advance goals.

Goals come from planning.goals (later rounds first). This loop does not search
every legal upgrade; it only places and upgrades those targets.
"""

from __future__ import annotations

from actions import Action, PlaceTower, StartRound, Upgrade
from catalog import Catalog
from data.enums import Tower, UpgradePath
from harness.simulated_harness import SimulatedHarness
from observation import GameSetup, Observation, PlacedTower
from planning import Planner
from planning.evaluate import (
    DEFAULT_BLOON_SPEED,
    RoundVerdictStatus,
    evaluate_round,
    path_fraction_in_range,
    path_length_units,
)
from planning.goals import Goal, select_goals
from system_flags import vprint

_PATHS = (UpgradePath.TOP, UpgradePath.MIDDLE, UpgradePath.BOTTOM)
_SURVIVE_MARGIN = 1.0


class GoalPlanner(Planner):
    def __init__(
        self,
        setup: GameSetup,
        towers: list[Tower],
        *,
        target_round: int = 40,
        max_shop_actions_per_round: int = 5,
        path_fraction: float = 0.12,
    ):
        self.setup = setup
        self.towers = towers
        self.target_round = target_round
        self.max_shop_actions_per_round = max_shop_actions_per_round
        self.path_fraction = path_fraction
        self._spot_cache: dict[Tower, tuple[float, float] | None] = {}

    def plan(self, observation: Observation, catalog: Catalog) -> list[Action]:
        del observation
        track = catalog.tracks.get_track_data(self.setup.track)
        if track is None:
            raise RuntimeError(f"no track data for {self.setup.track.value}")
        transit = path_length_units(track) / DEFAULT_BLOON_SPEED
        goals = select_goals(
            catalog,
            self.towers,
            self.setup.difficulty,
            self.target_round,
            transit=transit,
            path_fraction=self.path_fraction,
        )
        if not goals:
            raise RuntimeError("no goals for this tower pool and target round")
        goals = self._confirm_loadout(catalog, goals, track)
        for goal in goals:
            tiers = "/".join(str(goal.tiers[path]) for path in _PATHS)
            vprint(
                f"[goal] {goal.goal_id} {goal.tower.value} {tiers} "
                f"by r{goal.deadline}: {goal.reason}"
            )

        sim = SimulatedHarness()
        sim._catalog = catalog
        obs = sim.reset(self.setup)
        plan: list[Action] = []

        while obs.believed.round_index <= self.target_round:
            current = obs.believed.round_index
            current_rd = catalog.rounds.get_round_data(current)
            if current_rd is None:
                raise RuntimeError(f"no round data for {current}")
            for _ in range(self.max_shop_actions_per_round):
                verdict = evaluate_round(
                    obs, current_rd, catalog, clear_margin=_SURVIVE_MARGIN, track=track
                )
                action = self._choose(sim, obs, catalog, goals, failing=verdict.status != RoundVerdictStatus.PASS)
                if action is None:
                    break
                result = sim.step(action)
                if not result.ok:
                    raise RuntimeError(f"planner step failed: {result.error}")
                obs = result.observation
                plan.append(action)
                if isinstance(action, PlaceTower):
                    self._spot_cache.clear()
                self._assign_refs(goals, obs)

            verdict = evaluate_round(
                obs, current_rd, catalog, clear_margin=_SURVIVE_MARGIN, track=track
            )
            if verdict.status != RoundVerdictStatus.PASS:
                raise RuntimeError(
                    f"cannot clear r{current} with committed goals "
                    f"({verdict.status.value}, "
                    f"budget={verdict.damage_budget:.0f}/{verdict.rbe:.0f}, "
                    f"cash=${obs.believed.cash:.0f}). "
                    f"Partial plans are not returned."
                )

            result = sim.step(StartRound())
            if not result.ok:
                raise RuntimeError(f"StartRound failed: {result.error}")
            obs = result.observation
            plan.append(StartRound())
            self._spot_cache.clear()

        if obs.believed.round_index <= self.target_round:
            raise RuntimeError(
                f"plan incomplete: ended at r{obs.believed.round_index}, "
                f"target was {self.target_round}"
            )
        return plan

    def _confirm_loadout(
        self,
        catalog: Catalog,
        goals: list[Goal],
        track,
    ) -> list[Goal]:
        """Place the finished loadout on the real track and beef it until every round passes.

        Cash is ignored here. Acquisition is a later pass.
        """
        sim = SimulatedHarness()
        sim._catalog = catalog
        obs = self._materialize(sim, catalog, goals)
        for _ in range(80):
            short = None
            before = None
            for round_num in range(1, self.target_round + 1):
                round_data = catalog.rounds.get_round_data(round_num)
                if round_data is None:
                    break
                verdict = evaluate_round(
                    obs, round_data, catalog, clear_margin=_SURVIVE_MARGIN, track=track
                )
                if verdict.status != RoundVerdictStatus.PASS:
                    short = round_data
                    before = verdict
                    break
            if short is None or before is None:
                vprint(f"[goal] loadout clears r1 through r{self.target_round}")
                return goals
            step = self._best_loadout_step(sim, obs, catalog, goals, short, before)
            if step is None:
                raise RuntimeError(
                    f"loadout cannot clear r{short.round_num} "
                    f"({before.status.value}, "
                    f"budget={before.damage_budget:.0f}/{before.rbe:.0f}). "
                    f"No placed build in this tower pool increases that budget."
                )
            kind, payload = step
            if kind == "upgrade":
                goal, path = payload
                goal.tiers[path] += 1
                goal.deadline = min(goal.deadline, short.round_num)
                goal.reason += f"; +{path.value} for r{short.round_num}"
                vprint(
                    f"[goal] loadout +{path.value} on {goal.goal_id} for r{short.round_num}"
                )
            else:
                tower, action = payload
                goals.append(
                    Goal(
                        goal_id=action.ref,
                        tower=tower,
                        tiers={path: 0 for path in _PATHS},
                        deadline=short.round_num,
                        reason=f"real dps for r{short.round_num}",
                        requirements=frozenset(),
                        assigned_ref=action.ref,
                        position=action.position,
                    )
                )
                vprint(f"[goal] loadout place {tower.value} for r{short.round_num}")
            result = sim.step(action if kind == "place" else Upgrade(ref=payload[0].goal_id, upgrade_path=payload[1]))
            if not result.ok:
                raise RuntimeError(f"loadout step failed: {result.error}")
            obs = result.observation
            if kind == "place":
                self._spot_cache.clear()
        raise RuntimeError(
            f"loadout still short after extra buys through r{self.target_round}"
        )

    def _materialize(self, sim: SimulatedHarness, catalog: Catalog, goals: list[Goal]) -> Observation:
        obs = sim.reset(self.setup)
        sim._cash = 1e12
        self._spot_cache.clear()
        for goal in goals:
            goal.assigned_ref = goal.goal_id
            spot = self._spot(sim, goal.tower)
            if spot is None:
                raise RuntimeError(f"no placement for {goal.tower.value}")
            goal.position = spot
            result = sim.step(PlaceTower(tower=goal.tower, position=spot, ref=goal.goal_id))
            if not result.ok:
                raise RuntimeError(f"loadout place failed: {result.error}")
            obs = result.observation
            self._spot_cache.clear()
            placed = self._placed(obs, goal)
            while placed is not None and not goal.complete(placed):
                path = self._next_path(goal, placed)
                if path is None or path not in catalog.legal_upgrades(placed):
                    break
                result = sim.step(Upgrade(ref=goal.goal_id, upgrade_path=path))
                if not result.ok:
                    raise RuntimeError(f"loadout upgrade failed: {result.error}")
                obs = result.observation
                placed = self._placed(obs, goal)
        return obs

    def _best_loadout_step(self, sim, obs, catalog, goals, short, before):
        best = None
        best_score = 0.0
        for goal in goals:
            placed = self._placed(obs, goal)
            if placed is None:
                continue
            for path in catalog.legal_upgrades(placed):
                nxt = dict(goal.tiers)
                nxt[path] = goal.tiers[path] + 1
                if nxt[path] > 5:
                    continue
                if goal.requirements:
                    probe = PlacedTower(
                        tower=goal.tower,
                        position=placed.position,
                        ref=goal.goal_id,
                        upgrades=nxt,
                    )
                    from planning.evaluate import tower_matches_requirements
                    if not tower_matches_requirements(probe, catalog, goal.requirements):
                        continue
                action = Upgrade(ref=goal.goal_id, upgrade_path=path)
                cost = catalog.cost_upgrade(placed, path, self.setup.difficulty)
                fork = sim.clone()
                result = fork.step(action)
                if not result.ok:
                    continue
                after = evaluate_round(
                    result.observation, short, catalog, clear_margin=_SURVIVE_MARGIN
                )
                delta = after.damage_budget - before.damage_budget
                score = delta / cost if cost > 0 else 0.0
                if delta > 1.0 and score > best_score:
                    best_score = score
                    best = ("upgrade", (goal, path))
        if len(goals) < 16:
            for tower in self.towers:
                spot = self._spot(sim, tower)
                if spot is None:
                    continue
                ref = f"g{len(goals) + 1}"
                action = PlaceTower(tower=tower, position=spot, ref=ref)
                cost = catalog.cost_place(tower, self.setup.difficulty) * 1.5
                fork = sim.clone()
                result = fork.step(action)
                if not result.ok:
                    continue
                after = evaluate_round(
                    result.observation, short, catalog, clear_margin=_SURVIVE_MARGIN
                )
                delta = after.damage_budget - before.damage_budget
                score = delta / cost if cost > 0 else 0.0
                if delta > 1.0 and score > best_score:
                    best_score = score
                    best = ("place", (tower, action))
        return best

    def _choose(
        self,
        sim: SimulatedHarness,
        obs: Observation,
        catalog: Catalog,
        goals: list[Goal],
        *,
        failing: bool,
    ) -> Action | None:
        current = obs.believed.round_index
        if failing:
            current_rd = catalog.rounds.get_round_data(obs.believed.round_index)
            if current_rd is None:
                return None
            return self._survival_buy(sim, obs, catalog, goals, current_rd)

        incomplete = [
            goal for goal in goals if not goal.complete(self._placed(obs, goal))
        ]
        urgent = [
            goal for goal in incomplete if goal.requirements and self._due(goal, obs)
        ]
        ready = urgent or [
            goal for goal in incomplete if self._due(goal, obs) or goal.deadline <= current
        ]
        if not ready:
            ready = [goal for goal in incomplete if goal.deadline <= current + 8]
        for goal in sorted(ready, key=lambda item: (item.deadline, item.goal_id)):
            action = self._next_step(sim, obs, catalog, goal)
            if action is not None:
                return action
        return None

    def _due(self, goal: Goal, obs: Observation) -> bool:
        placed = self._placed(obs, goal)
        steps = goal.steps_remaining(placed)
        return goal.deadline - obs.believed.round_index <= max(steps * 3, 8)

    def _earliest_short(self, obs: Observation, catalog: Catalog, horizon: int):
        last = min(self.target_round, obs.believed.round_index + horizon)
        for round_num in range(obs.believed.round_index, last + 1):
            round_data = catalog.rounds.get_round_data(round_num)
            if round_data is None:
                return None
            verdict = evaluate_round(
                obs, round_data, catalog, clear_margin=_SURVIVE_MARGIN
            )
            if verdict.status != RoundVerdictStatus.PASS:
                return round_data
        return None

    def _survival_buy(
        self,
        sim: SimulatedHarness,
        obs: Observation,
        catalog: Catalog,
        goals: list[Goal],
        current_rd,
    ) -> Action | None:
        before = evaluate_round(obs, current_rd, catalog, clear_margin=_SURVIVE_MARGIN)
        best: Action | None = None
        best_key: tuple = ()
        for goal in goals:
            action = self._next_step(sim, obs, catalog, goal)
            if action is None:
                continue
            fork = sim.clone()
            result = fork.step(action)
            if not result.ok:
                continue
            after = evaluate_round(
                result.observation, current_rd, catalog, clear_margin=_SURVIVE_MARGIN
            )
            key = (
                0 if after.status == RoundVerdictStatus.PASS else 1,
                -after.damage_budget,
            )
            if best is None or key < best_key:
                if after.damage_budget > before.damage_budget + 1.0 or after.status == RoundVerdictStatus.PASS:
                    best = action
                    best_key = key
        return best

    def _emergency_place(self, sim, obs, catalog, before, current_rd):
        """One extra tower when committed goals cannot move the current round."""
        best = None
        best_budget = before.damage_budget
        for tower in self.towers:
            cost = catalog.cost_place(tower, self.setup.difficulty)
            if obs.believed.cash < cost:
                continue
            spot = self._spot(sim, tower)
            if spot is None:
                continue
            ref = f"fill_{tower.value}_{obs.believed.round_index}_{len(obs.believed.placed)}"
            action = PlaceTower(tower=tower, position=spot, ref=ref)
            fork = sim.clone()
            result = fork.step(action)
            if not result.ok:
                continue
            after = evaluate_round(
                result.observation, current_rd, catalog, clear_margin=_SURVIVE_MARGIN
            )
            if after.damage_budget > best_budget + 1.0:
                best = action
                best_budget = after.damage_budget
        return best

    def _next_step(
        self,
        sim: SimulatedHarness,
        obs: Observation,
        catalog: Catalog,
        goal: Goal,
    ) -> Action | None:
        placed = self._placed(obs, goal)
        if placed is None:
            cost = catalog.cost_place(goal.tower, self.setup.difficulty)
            if obs.believed.cash < cost:
                return None
            spot = goal.position or self._spot(sim, goal.tower)
            if spot is None:
                return None
            goal.assigned_ref = goal.goal_id
            return PlaceTower(tower=goal.tower, position=spot, ref=goal.goal_id)

        affordable: list[tuple[float, UpgradePath]] = []
        for path in _PATHS:
            if placed.upgrades[path] >= goal.tiers[path]:
                continue
            if path not in catalog.legal_upgrades(placed):
                continue
            cost = catalog.cost_upgrade(placed, path, self.setup.difficulty)
            if obs.believed.cash < cost:
                continue
            affordable.append((cost, path))
        if not affordable:
            return None
        _cost, path = min(affordable)
        return Upgrade(ref=placed.ref, upgrade_path=path)

    def _next_path(self, goal: Goal, placed: PlacedTower) -> UpgradePath | None:
        behind = [path for path in _PATHS if placed.upgrades[path] < goal.tiers[path]]
        if not behind:
            return None
        return max(behind, key=lambda path: goal.tiers[path] - placed.upgrades[path])

    def _placed(self, obs: Observation, goal: Goal) -> PlacedTower | None:
        ref = goal.assigned_ref or goal.goal_id
        return next((tower for tower in obs.believed.placed if tower.ref == ref), None)

    def _assign_refs(self, goals: list[Goal], obs: Observation) -> None:
        refs = {tower.ref for tower in obs.believed.placed}
        for goal in goals:
            if goal.goal_id in refs:
                goal.assigned_ref = goal.goal_id

    def _spot(self, sim: SimulatedHarness, tower: Tower) -> tuple[float, float] | None:
        if tower not in self._spot_cache:
            spots = sim.placement_candidates(tower)
            track = sim._track_data
            catalog = sim._catalog
            best: tuple[float, float] | None = None
            best_frac = -1.0
            if track is not None and catalog is not None:
                for spot in spots:
                    probe = PlacedTower(
                        tower=tower, position=spot.position, ref="_spot"
                    )
                    frac = path_fraction_in_range(probe, track, catalog)
                    if frac > best_frac:
                        best_frac = frac
                        best = spot.position
            elif spots:
                best = spots[0].position
            self._spot_cache[tower] = best
        return self._spot_cache[tower]
