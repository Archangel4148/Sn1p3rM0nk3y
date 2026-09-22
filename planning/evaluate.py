"""Estimated pass/fail for a board vs upcoming round data.

Not a bloon sim. Hard fail = something on the round nothing can interact with
(estimated leak → lives to 0). Soft fail = coverage ok but clear rate looks
too low for that round's RBE (likely leak). Pass = estimated survive.

Heroes are ignored in coverage/DPS until hero leveling exists — do not count
on PlaceHero for evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from actions import Action, StartRound
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
from harness import Harness
from harness.simulated_harness import SimulatedHarness
from observation import GameSetup, Observation, PlacedTower
from system_flags import vprint


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
    missing: tuple[CoverageType, ...] = ()
    detail: str = ""

    @property
    def estimated_lose(self) -> bool:
        return self.status != RoundVerdictStatus.PASS


@dataclass(frozen=True)
class PlanEvaluation:
    # True only if every StartRound was an estimated survive and the tape ran.
    ok: bool
    rounds: tuple[RoundVerdict, ...]
    first_loss_round: int | None = None
    error: str | None = None

    @property
    def estimated_lose(self) -> bool:
        return not self.ok


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


def evaluate_round(
    observation: Observation,
    round_data: RoundData,
    catalog: Catalog,
    *,
    soft_clear_factor: float = 0.05,
) -> RoundVerdict:
    """Score the current board against one upcoming round.

    soft_clear_factor: require board_dps >= rbe * factor (very rough clear-rate gate).
    """
    placed = observation.believed.placed
    dps = board_dps(placed, catalog)
    coverage = board_coverage(placed, catalog)
    need = round_requirements(round_data)
    missing = tuple(sorted((c for c in need if not coverage[c]), key=lambda c: c.value))

    if missing:
        return RoundVerdict(
            round_num=round_data.round_num,
            status=RoundVerdictStatus.HARD_FAIL,
            rbe=round_data.rbe,
            board_dps=dps,
            missing=missing,
            detail=f"missing coverage: {', '.join(c.value for c in missing)}",
        )

    required = round_data.rbe * soft_clear_factor
    if dps < required:
        return RoundVerdict(
            round_num=round_data.round_num,
            status=RoundVerdictStatus.SOFT_FAIL,
            rbe=round_data.rbe,
            board_dps=dps,
            detail=f"dps {dps:.1f} < required {required:.1f} (rbe {round_data.rbe})",
        )

    return RoundVerdict(
        round_num=round_data.round_num,
        status=RoundVerdictStatus.PASS,
        rbe=round_data.rbe,
        board_dps=dps,
        detail=f"dps {dps:.1f} ok for rbe {round_data.rbe}",
    )


def evaluate_plan(
    setup: GameSetup,
    plan: list[Action],
    *,
    catalog: Catalog | None = None,
    harness: Harness | None = None,
    soft_clear_factor: float = 0.05,
    stop_on_estimated_loss: bool = True,
) -> PlanEvaluation:
    """Replay the plan on a harness; before each StartRound, score the upcoming round."""
    catalog = catalog or Catalog()
    harness = harness or SimulatedHarness()
    obs = harness.reset(setup)
    verdicts: list[RoundVerdict] = []

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
                obs, round_data, catalog, soft_clear_factor=soft_clear_factor
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
