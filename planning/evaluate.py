"""Estimated pass/fail for a board vs upcoming round data.

Not a bloon sim. Hard fail = something on the round nothing can interact with
(estimated leak → lives to 0). Soft fail = coverage ok but estimated damage
budget while bloons are in range is below the round's RBE (likely leak).
Pass = estimated survive.

Damage budget ≈ sum(tower_dps * path_transit_s * path_fraction_in_range).
Path fraction comes from flow points inside each tower's range; transit time
is path length / an assumed bloon speed (default ~red).

Heroes are ignored in coverage/DPS until hero leveling exists — do not count
on PlaceHero for evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from actions import Action, PlaceHero, PlaceTower, StartRound, Upgrade
from catalog import Catalog
from data.enums import (
    DAMAGE_TYPE_BY_COVERAGE,
    BloonModifier,
    BloonType,
    CoverageType,
    DamageType,
    Tower,
)
from data.rounds_data import RoundData
from data.track_data import TrackData, TrackDatabase
from harness import Harness
from harness.placement import attack_range_px
from harness.simulated_harness import SimulatedHarness
from observation import GameSetup, Observation, PlacedTower
from system_flags import PIXELS_PER_BLOONS_UNIT, vprint

# Approx red-bloon speed in game units/sec. Faster bloons => tighter soft gate.
DEFAULT_BLOON_SPEED = 25.0


class RoundVerdictStatus(StrEnum):
    PASS = "pass"
    SOFT_FAIL = "soft_fail"  # estimated underpowered → likely lives loss
    HARD_FAIL = "hard_fail"  # unblockable property → estimated lives loss


@dataclass(frozen=True)
class RoundVerdict:
    round_num: int
    status: RoundVerdictStatus
    rbe: int
    board_dps: float
    effective_dps: float = 0.0
    damage_budget: float = 0.0
    missing: tuple[CoverageType, ...] = ()
    detail: str = ""

    @property
    def estimated_lose(self) -> bool:
        # return self.status != RoundVerdictStatus.PASS
        return self.status == RoundVerdictStatus.HARD_FAIL


_TRACK_DB = TrackDatabase()


@dataclass(frozen=True)
class PlanEvaluation:
    # True only if the tape ran, every purchase was legal, and no hard loss.
    ok: bool
    rounds: tuple[RoundVerdict, ...]
    first_loss_round: int | None = None
    error: str | None = None
    illegal_purchase: str | None = None

    @property
    def estimated_lose(self) -> bool:
        return not self.ok and self.illegal_purchase is None


def purchase_illegality(
    observation: Observation,
    setup: GameSetup,
    action: Action,
    catalog: Catalog,
) -> str | None:
    """Return a reason the buy is illegal, or None if it is allowed.

    Covers affordability, crosspath rules, refs, and known catalog entries.
    Placement terrain is not checked here (harness / candidates own that).
    """
    believed = observation.believed

    if isinstance(action, PlaceTower):
        if catalog.towers.get_tower_data(action.tower) is None:
            return f"unknown_tower:{action.tower.value}"
        if any(p.ref == action.ref for p in believed.placed):
            return f"duplicate_ref:{action.ref}"
        cost = catalog.cost_place(action.tower, setup.difficulty)
        if believed.cash < cost:
            return f"cannot_afford:{action.tower.value}:${cost:.0f}>${believed.cash:.0f}"
        return None

    if isinstance(action, PlaceHero):
        if believed.hero_placed:
            return "hero_already_placed"
        if any(p.ref == action.ref for p in believed.placed):
            return f"duplicate_ref:{action.ref}"
        if catalog.heroes.get_hero_data(setup.hero) is None:
            return f"unknown_hero:{setup.hero.value}"
        cost = catalog.cost_place(setup.hero, setup.difficulty)
        if believed.cash < cost:
            return f"cannot_afford:hero:${cost:.0f}>${believed.cash:.0f}"
        return None

    if isinstance(action, Upgrade):
        placed = next((p for p in believed.placed if p.ref == action.ref), None)
        if placed is None:
            return f"unknown_ref:{action.ref}"
        if not isinstance(placed.tower, Tower):
            return f"upgrading_hero:{action.ref}"
        if action.upgrade_path not in catalog.legal_upgrades(placed):
            cross = "/".join(
                str(placed.upgrades[p]) for p in placed.upgrades
            )
            return (
                f"illegal_upgrade:{action.ref}:{action.upgrade_path.value}"
                f"(from {cross})"
            )
        cost = catalog.cost_upgrade(placed, action.upgrade_path, setup.difficulty)
        if believed.cash < cost:
            return (
                f"cannot_afford:{action.ref}:{action.upgrade_path.value}"
                f":${cost:.0f}>${believed.cash:.0f}"
            )
        return None

    return None


def bloon_group_requirements(group) -> set[CoverageType]:
    """Coverage the board must have to interact with this group at all."""
    need: set[CoverageType] = set()
    if BloonModifier.CAMO in group.modifiers:
        need.add(CoverageType.CAMO)

    base = group.base_type
    if base == BloonType.LEAD:
        need.add(CoverageType.LEAD)
    elif base == BloonType.PURPLE:
        need.add(CoverageType.PURPLE)
    elif base == BloonType.BLACK:
        need.add(CoverageType.BLACK)
    elif base == BloonType.WHITE:
        need.add(CoverageType.WHITE)
    elif base == BloonType.ZEBRA:
        need.add(CoverageType.BLACK)
        need.add(CoverageType.WHITE)
    elif base == BloonType.DDT:
        need.add(CoverageType.CAMO)
        need.add(CoverageType.LEAD)
    return need


def round_requirements(round_data: RoundData) -> set[CoverageType]:
    need: set[CoverageType] = set()
    for group in round_data.bloon_groups:
        need |= bloon_group_requirements(group)
    return need


def tower_damage_type(placed: PlacedTower, catalog: Catalog) -> DamageType | None:
    if not isinstance(placed.tower, Tower):
        return None

    data = catalog.towers.get_tower_data(placed.tower)
    if data is None:
        return None
    current = data.damage_type
    best: DamageType | None = DamageType(current) if current else None

    for path, tier in placed.upgrades.items():
        if tier <= 0:
            continue
        upgrade = catalog.upgrades.get_upgrade(placed.tower, path, tier)
        if upgrade is None or not upgrade.damage_type:
            continue
        try:
            best = DamageType(upgrade.damage_type)
        except ValueError:
            continue
    return best


def tower_coverage(placed: PlacedTower, catalog: Catalog) -> dict[CoverageType, bool]:
    coverage = {c: False for c in CoverageType}
    if not isinstance(placed.tower, Tower):
        return coverage

    data = catalog.towers.get_tower_data(placed.tower)
    if data is not None:
        coverage[CoverageType.CAMO] = bool(data.base_sees_camo)
    for path, tier in placed.upgrades.items():
        for t in range(1, tier + 1):
            upgrade = catalog.upgrades.get_upgrade(placed.tower, path, t)
            if upgrade is None:
                continue
            if upgrade.grants_camo:
                coverage[CoverageType.CAMO] = True
            if upgrade.grants_lead:
                coverage[CoverageType.LEAD] = True

    dtype = tower_damage_type(placed, catalog)
    if dtype is not None and dtype in DAMAGE_TYPE_BY_COVERAGE:
        for c in DAMAGE_TYPE_BY_COVERAGE[dtype]:
            coverage[c] = True
    return coverage


def board_coverage(placed: tuple[PlacedTower, ...], catalog: Catalog) -> dict[CoverageType, bool]:
    board = {c: False for c in CoverageType}
    for tower in placed:
        if not isinstance(tower.tower, Tower):
            continue
        for key, value in tower_coverage(tower, catalog).items():
            board[key] = board[key] or value
    return board


def tower_dps(placed: PlacedTower, catalog: Catalog) -> float:
    if not isinstance(placed.tower, Tower):
        return 0.0

    data = catalog.towers.get_tower_data(placed.tower)
    if data is None:
        return 0.0

    damage = data.damage or 1.0
    cooldown = data.cooldown or 1.0
    pierce = data.pierce or 1.0
    projectiles = data.projectiles or 1.0

    for path, tier in placed.upgrades.items():
        for t in range(1, tier + 1):
            upgrade = catalog.upgrades.get_upgrade(placed.tower, path, t)
            if upgrade is None:
                continue
            if upgrade.damage is not None:
                damage = upgrade.damage or 1.0
            if upgrade.cooldown is not None:
                cooldown = upgrade.cooldown or 1.0
            if upgrade.pierce is not None:
                pierce = upgrade.pierce or 1.0
            if upgrade.projectiles is not None:
                projectiles = upgrade.projectiles or 1.0

    if cooldown <= 0:
        return 0.0
    return float((damage * pierce * projectiles) / cooldown)


def board_dps(placed: tuple[PlacedTower, ...], catalog: Catalog) -> float:
    return sum(
        tower_dps(tower, catalog)
        for tower in placed
        if isinstance(tower.tower, Tower)
    )


def path_length_units(track: TrackData) -> float:
    flow = np.asarray(track.flow_points, dtype=float)
    if len(flow) < 2:
        return 0.0
    return float(np.sqrt(((flow[1:] - flow[:-1]) ** 2).sum(axis=1)).sum()) / PIXELS_PER_BLOONS_UNIT


def path_fraction_in_range(
    placed: PlacedTower,
    track: TrackData,
    catalog: Catalog,
) -> float:
    """Fraction of flow points that fall inside this tower's attack range."""
    if not isinstance(placed.tower, Tower):
        return 0.0
    flow = np.asarray(track.flow_points, dtype=float)
    if len(flow) == 0:
        return 0.0

    h, w = track.size
    x = placed.position[0] * w
    y = placed.position[1] * h
    range_px = attack_range_px(catalog, placed.tower)
    if range_px <= 0:
        return 0.0

    in_range = np.sum((flow[:, 0] - x) ** 2 + (flow[:, 1] - y) ** 2 < float(range_px * range_px))
    return float(in_range) / float(len(flow))


def effective_board_dps(
    placed: tuple[PlacedTower, ...],
    track: TrackData,
    catalog: Catalog,
) -> float:
    """Raw DPS scaled by how much of the path each tower can see."""
    total = 0.0
    for tower in placed:
        if not isinstance(tower.tower, Tower):
            continue
        total += tower_dps(tower, catalog) * path_fraction_in_range(tower, track, catalog)
    return total


def evaluate_round(
    observation: Observation,
    round_data: RoundData,
    catalog: Catalog,
    *,
    bloon_speed: float = DEFAULT_BLOON_SPEED,
    clear_margin: float = 1.0,
    track: TrackData | None = None,
) -> RoundVerdict:
    """Score the current board against one upcoming round.

    Soft gate: damage_budget = effective_dps * (path_length / bloon_speed)
    must be >= rbe * clear_margin. effective_dps weights each tower by the
    fraction of flow points inside its range.
    """
    placed = observation.believed.placed
    dps = board_dps(placed, catalog)
    coverage = board_coverage(placed, catalog)
    need = round_requirements(round_data)
    missing = tuple(sorted((c for c in need if not coverage[c]), key=lambda c: c.value))

    track = track or _TRACK_DB.get_track_data(observation.believed.track)
    if track is None:
        return RoundVerdict(
            round_num=round_data.round_num,
            status=RoundVerdictStatus.HARD_FAIL,
            rbe=round_data.rbe,
            board_dps=dps,
            detail=f"no track data for {observation.believed.track.value}",
        )

    eff = effective_board_dps(placed, track, catalog)
    transit = path_length_units(track) / max(bloon_speed, 1e-6)
    budget = eff * transit

    if missing:
        return RoundVerdict(
            round_num=round_data.round_num,
            status=RoundVerdictStatus.HARD_FAIL,
            rbe=round_data.rbe,
            board_dps=dps,
            effective_dps=eff,
            damage_budget=budget,
            missing=missing,
            detail=f"missing coverage: {', '.join(c.value for c in missing)}",
        )

    required = round_data.rbe * clear_margin
    if budget < required:
        return RoundVerdict(
            round_num=round_data.round_num,
            status=RoundVerdictStatus.SOFT_FAIL,
            rbe=round_data.rbe,
            board_dps=dps,
            effective_dps=eff,
            damage_budget=budget,
            detail=(
                f"budget {budget:.0f} < required {required:.0f} "
                f"(eff_dps={eff:.1f} raw_dps={dps:.1f} transit={transit:.1f}s "
                f"rbe={round_data.rbe})"
            ),
        )

    return RoundVerdict(
        round_num=round_data.round_num,
        status=RoundVerdictStatus.PASS,
        rbe=round_data.rbe,
        board_dps=dps,
        effective_dps=eff,
        damage_budget=budget,
        detail=(
            f"budget {budget:.0f} ok for rbe {round_data.rbe} "
            f"(eff_dps={eff:.1f} raw_dps={dps:.1f} transit={transit:.1f}s)"
        ),
    )


def evaluate_plan(
    setup: GameSetup,
    plan: list[Action],
    *,
    catalog: Catalog | None = None,
    harness: Harness | None = None,
    bloon_speed: float = DEFAULT_BLOON_SPEED,
    clear_margin: float = 1.0,
    stop_on_estimated_loss: bool = True,
) -> PlanEvaluation:
    """Replay the plan on a harness; before each StartRound, score the upcoming round.

    Shop actions are checked for legal purchases (cash, crosspath, refs) before
    the harness steps them.
    """
    catalog = catalog or Catalog()
    harness = harness or SimulatedHarness()
    obs = harness.reset(setup)
    verdicts: list[RoundVerdict] = []
    track = _TRACK_DB.get_track_data(setup.track)

    for i, action in enumerate(plan):
        if isinstance(action, StartRound):
            round_data = catalog.rounds.get_round_data(obs.believed.round_index)
            if round_data is None:
                return PlanEvaluation(
                    ok=False,
                    rounds=tuple(verdicts),
                    error=f"no round data for {obs.believed.round_index}",
                )
            verdict = evaluate_round(
                obs,
                round_data,
                catalog,
                bloon_speed=bloon_speed,
                clear_margin=clear_margin,
                track=track,
            )
            verdicts.append(verdict)
            vprint(
                f"[eval] round {verdict.round_num}: {verdict.status.value} "
                f"({verdict.detail})"
            )
            if verdict.estimated_lose and stop_on_estimated_loss:
                return PlanEvaluation(
                    ok=False,
                    rounds=tuple(verdicts),
                    first_loss_round=verdict.round_num,
                )

        illegal = purchase_illegality(obs, setup, action, catalog)
        if illegal is not None:
            vprint(f"[eval] illegal purchase at step {i}: {illegal}")
            return PlanEvaluation(
                ok=False,
                rounds=tuple(verdicts),
                error=f"step {i}: {illegal}",
                illegal_purchase=illegal,
            )

        result = harness.step(action)
        obs = result.observation
        if not result.ok:
            return PlanEvaluation(
                ok=False,
                rounds=tuple(verdicts),
                error=f"step {i} failed: {result.error}",
            )

    lost = next((v for v in verdicts if v.estimated_lose), None)
    return PlanEvaluation(
        ok=lost is None,
        rounds=tuple(verdicts),
        first_loss_round=None if lost is None else lost.round_num,
    )
