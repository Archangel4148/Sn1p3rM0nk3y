"""Pick landmark tower builds from later rounds, then the forward planner buys them.

Virtual DPS assumes each goal is fully built on its deadline and absent before
that, so early rounds still get their own cheap towers.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from catalog import Catalog
from data.enums import BloonsDifficulty, CoverageType, Tower, UpgradePath
from data.rounds_data import RoundData
from observation import PlacedTower
from planning.evaluate import (
    coverage_label,
    round_rbe_by_coverage,
    tower_dps,
    tower_matches_requirements,
)

_PATHS = (UpgradePath.TOP, UpgradePath.MIDDLE, UpgradePath.BOTTOM)


@dataclass
class Goal:
    goal_id: str
    tower: Tower
    tiers: dict[UpgradePath, int]
    deadline: int
    reason: str
    requirements: frozenset[CoverageType] = field(default_factory=frozenset)
    assigned_ref: str | None = None
    position: tuple[float, float] | None = None

    def placed_view(self) -> PlacedTower:
        return PlacedTower(
            tower=self.tower,
            position=(0.0, 0.0),
            ref=self.goal_id,
            upgrades={path: int(self.tiers[path]) for path in _PATHS},
        )

    def steps_remaining(self, placed: PlacedTower | None) -> int:
        tiers = sum(max(0, self.tiers[path] - (0 if placed is None else placed.upgrades[path])) for path in _PATHS)
        return tiers + (0 if placed is not None else 1)

    def complete(self, placed: PlacedTower | None) -> bool:
        if placed is None:
            return False
        return all(placed.upgrades[path] >= self.tiers[path] for path in _PATHS)


def _zero_tiers() -> dict[UpgradePath, int]:
    return {path: 0 for path in _PATHS}


def _legal(tiers: dict[UpgradePath, int]) -> bool:
    values = [tiers[path] for path in _PATHS]
    if sum(value > 0 for value in values) > 2:
        return False
    return sum(value >= 3 for value in values) <= 1


def _config_cost(
    catalog: Catalog,
    tower: Tower,
    tiers: dict[UpgradePath, int],
    difficulty: BloonsDifficulty,
) -> float:
    total = catalog.cost_place(tower, difficulty)
    for path in _PATHS:
        for tier in range(1, tiers[path] + 1):
            upgrade = catalog.upgrades.get_upgrade(tower, path, tier)
            if upgrade is None:
                return float("inf")
            total += upgrade.cost_for(difficulty)
    return total


def _matches(
    catalog: Catalog, tower: Tower, tiers: dict[UpgradePath, int], req: frozenset[CoverageType]
) -> bool:
    placed = PlacedTower(
        tower=tower, position=(0.0, 0.0), ref="_", upgrades=dict(tiers)
    )
    return tower_matches_requirements(placed, catalog, req)


def cheapest_build(
    catalog: Catalog,
    towers: list[Tower],
    req: frozenset[CoverageType],
    difficulty: BloonsDifficulty,
) -> tuple[Tower, dict[UpgradePath, int], float] | None:
    best: tuple[Tower, dict[UpgradePath, int], float] | None = None
    best_key: tuple = ()
    for tower in towers:
        for top in range(6):
            for mid in range(6):
                for bot in range(6):
                    tiers = {
                        UpgradePath.TOP: top,
                        UpgradePath.MIDDLE: mid,
                        UpgradePath.BOTTOM: bot,
                    }
                    if not _legal(tiers) or not _matches(catalog, tower, tiers, req):
                        continue
                    cost = _config_cost(catalog, tower, tiers, difficulty)
                    key = (cost, top + mid + bot)
                    if best is None or key < best_key:
                        best = (tower, tiers, cost)
                        best_key = key
    return best


def _binding(
    goals: list[Goal],
    catalog: Catalog,
    round_data: RoundData,
    transit: float,
    path_fraction: float,
) -> tuple[float, frozenset[CoverageType]]:
    active = [goal for goal in goals if goal.deadline <= round_data.round_num]
    buckets = round_rbe_by_coverage(round_data)
    total_rbe = float(round_data.rbe) if round_data.rbe > 0 else 1.0
    worst_ratio = float("inf")
    worst_req: frozenset[CoverageType] = frozenset()
    for req, bucket_rbe in buckets.items():
        if bucket_rbe <= 1e-9:
            continue
        dps = 0.0
        for goal in active:
            placed = goal.placed_view()
            if tower_matches_requirements(placed, catalog, req):
                dps += tower_dps(placed, catalog)
        budget = dps * path_fraction * transit
        ratio = budget / bucket_rbe
        if ratio < worst_ratio:
            worst_ratio = ratio
            worst_req = req
    if worst_ratio == float("inf"):
        return 0.0, frozenset()
    return worst_ratio * total_rbe, worst_req


def _can_increment(catalog: Catalog, goal: Goal, path: UpgradePath) -> bool:
    nxt = dict(goal.tiers)
    nxt[path] = goal.tiers[path] + 1
    # Tier 5 prices starve the rest of the loadout. Stop beef at tier 4.
    if nxt[path] > 4 or not _legal(nxt):
        return False
    if catalog.upgrades.get_upgrade(goal.tower, path, nxt[path]) is None:
        return False
    if goal.requirements and not _matches(catalog, goal.tower, nxt, goal.requirements):
        return False
    return True


def select_goals(
    catalog: Catalog,
    towers: list[Tower],
    difficulty: BloonsDifficulty,
    target_round: int,
    *,
    transit: float,
    path_fraction: float = 0.12,
    survive_margin: float = 1.0,
    max_goals: int = 12,
    max_beef_steps: int = 40,
) -> list[Goal]:
    """Coverage builds for each typed bucket, then extra DPS until each round clears."""
    needed: dict[frozenset[CoverageType], int] = {}
    rounds: list[RoundData] = []
    for round_num in range(1, target_round + 1):
        round_data = catalog.rounds.get_round_data(round_num)
        if round_data is None:
            break
        rounds.append(round_data)
        for req, rbe in round_rbe_by_coverage(round_data).items():
            if req and rbe > 1e-9 and req not in needed:
                needed[req] = round_num

    goals: list[Goal] = []
    for req, deadline in sorted(needed.items(), key=lambda item: (-len(item[0]), item[1])):
        if any(_matches(catalog, goal.tower, goal.tiers, req) for goal in goals):
            continue
        build = cheapest_build(catalog, towers, req, difficulty)
        if build is None:
            continue
        tower, tiers, _cost = build
        goals.append(
            Goal(
                goal_id=f"g{len(goals) + 1}",
                tower=tower,
                tiers=tiers,
                deadline=deadline,
                reason=f"coverage {coverage_label(req)} by r{deadline}",
                requirements=req,
            )
        )

    for _ in range(max_beef_steps):
        short: RoundData | None = None
        old_budget = 0.0
        binding_req: frozenset[CoverageType] = frozenset()
        for round_data in rounds:
            budget, req = _binding(goals, catalog, round_data, transit, path_fraction)
            if budget < round_data.rbe * survive_margin:
                short = round_data
                old_budget = budget
                binding_req = req
                break
        if short is None:
            break

        best_score = 0.0
        best: tuple | None = None

        for goal in goals:
            for path in _PATHS:
                if not _can_increment(catalog, goal, path):
                    continue
                upgrade = catalog.upgrades.get_upgrade(
                    goal.tower, path, goal.tiers[path] + 1
                )
                assert upgrade is not None
                cost = upgrade.cost_for(difficulty)
                goal.tiers[path] += 1
                budget, _req = _binding(goals, catalog, short, transit, path_fraction)
                goal.tiers[path] -= 1
                delta = budget - old_budget
                score = delta / cost if cost > 0 else 0.0
                if delta > 1.0 and score > best_score:
                    best_score = score
                    best = ("upgrade", goal, path, short.round_num)

        if len(goals) < max_goals:
            for tower in towers:
                tiers = _zero_tiers()
                if binding_req and not _matches(catalog, tower, tiers, binding_req):
                    continue
                cost = catalog.cost_place(tower, difficulty) * 1.5
                goals.append(
                    Goal(
                        goal_id="_probe",
                        tower=tower,
                        tiers=tiers,
                        deadline=short.round_num,
                        reason="",
                        requirements=binding_req,
                    )
                )
                budget, _req = _binding(goals, catalog, short, transit, path_fraction)
                goals.pop()
                delta = budget - old_budget
                score = delta / cost if cost > 0 else 0.0
                if delta > 1.0 and score > best_score:
                    best_score = score
                    best = ("place", tower, binding_req, short.round_num)

        if best is None:
            break
        if best[0] == "upgrade":
            _kind, goal, path, round_num = best
            goal.tiers[path] += 1
            goal.deadline = min(goal.deadline, round_num)
            goal.reason += f"; +{path.value} for r{round_num}"
        else:
            _kind, tower, req, round_num = best
            goals.append(
                Goal(
                    goal_id=f"g{len(goals) + 1}",
                    tower=tower,
                    tiers=_zero_tiers(),
                    deadline=round_num,
                    reason=f"dps for r{round_num} ({coverage_label(req)})",
                    requirements=req,
                )
            )

    return goals
