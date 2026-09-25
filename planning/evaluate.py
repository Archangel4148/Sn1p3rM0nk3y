"""Estimated pass/fail for a board vs upcoming round data.

Not a bloon sim. Hard fail = something on the round nothing can interact with
(estimated leak → lives to 0). Soft fail = coverage ok but estimated damage
budget while bloons are in range is below the round's RBE (also a leak /
estimated lose). Pass = estimated survive.

Damage is typed by coverage interaction, not a single board DPS. Round RBE
is split into buckets (camo, lead, purple, black, white, zebra=black+white,
camo+lead, unrestricted, …). A tower only contributes path-weighted DPS to
a bucket if it matches every required flag — camo detection and/or
damage-type coverage from the catalog (Sharp/Explosion/…). That keeps ABR
camo rushes (and purple/lead) from looking fine with blind high-DPS towers.
Transit ≈ path length / assumed bloon speed.

Heroes are ignored in coverage/DPS until hero leveling exists — do not count
on PlaceHero for evaluation.
"""

from __future__ import annotations

import math
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
    UpgradePath,
)
from data.rounds_data import BloonGroup, RoundData
from data.track_data import TrackData, TrackDatabase
from harness import Harness
from harness.placement import attack_range_px
from harness.simulated_harness import SimulatedHarness
from observation import GameSetup, Observation, PlacedTower
from system_flags import PIXELS_PER_BLOONS_UNIT, vprint

# Approx red-bloon speed in game units/sec. Faster bloons => tighter soft gate.
DEFAULT_BLOON_SPEED = 25.0

# Approximate single-bloon RBE (pre-children). Used to split round.rbe across groups.
_BLOON_RBE: dict[BloonType, float] = {
    BloonType.RED: 1,
    BloonType.BLUE: 2,
    BloonType.GREEN: 3,
    BloonType.YELLOW: 4,
    BloonType.PINK: 5,
    BloonType.BLACK: 11,
    BloonType.WHITE: 11,
    BloonType.PURPLE: 11,
    BloonType.ZEBRA: 23,
    BloonType.LEAD: 23,
    BloonType.RAINBOW: 47,
    BloonType.CERAMIC: 104,
    BloonType.MOAB: 616,
    BloonType.BFB: 3164,
    BloonType.ZOMG: 16656,
    BloonType.DDT: 816,
    BloonType.BAD: 55760,
}


class RoundVerdictStatus(StrEnum):
    PASS = "pass"
    SOFT_FAIL = "soft_fail"  # estimated underpowered → likely lives loss
    HARD_FAIL = "hard_fail"  # unblockable property → estimated lives loss


@dataclass(frozen=True)
class TypedBudget:
    """One soft-gate bucket: RBE that needs a specific coverage set."""

    requirements: frozenset[CoverageType]
    rbe: float
    effective_dps: float
    budget: float

    @property
    def label(self) -> str:
        return coverage_label(self.requirements)


@dataclass(frozen=True)
class RoundVerdict:
    round_num: int
    status: RoundVerdictStatus
    rbe: int
    board_dps: float
    effective_dps: float = 0.0
    damage_budget: float = 0.0
    missing: tuple[CoverageType, ...] = ()
    typed_budgets: tuple[TypedBudget, ...] = ()
    detail: str = ""

    @property
    def estimated_lose(self) -> bool:
        return self.status != RoundVerdictStatus.PASS


_TRACK_DB = TrackDatabase()


@dataclass(frozen=True)
class PlanEvaluation:
    # True only if the tape ran, every purchase was legal, and no round leaked
    # (hard or soft fail).
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


def estimate_group_rbe(group: BloonGroup) -> float:
    """Rough RBE for one group (scaled later to match round.rbe)."""
    base = _BLOON_RBE.get(group.base_type, 1.0)
    if BloonModifier.FORTIFIED in group.modifiers:
        base *= 2.0
    return base * float(group.count)


def round_rbe_by_coverage(
    round_data: RoundData,
) -> dict[frozenset[CoverageType], float]:
    """Split round RBE into buckets keyed by required coverage set.

    Empty frozenset = unrestricted (any tower). Camo-only groups land in
    frozenset({CAMO}), CamoLead in {CAMO, LEAD}, etc. Group estimates are
    scaled so bucket totals match round_data.rbe.
    """
    raw: dict[frozenset[CoverageType], float] = {}
    for group in round_data.bloon_groups:
        key = frozenset(bloon_group_requirements(group))
        raw[key] = raw.get(key, 0.0) + estimate_group_rbe(group)

    total_raw = sum(raw.values())
    if total_raw <= 0:
        return {frozenset(): float(round_data.rbe)}

    scale = float(round_data.rbe) / total_raw
    return {key: value * scale for key, value in raw.items()}


def tower_matches_requirements(
    placed: PlacedTower,
    catalog: Catalog,
    requirements: frozenset[CoverageType],
) -> bool:
    if not requirements:
        return isinstance(placed.tower, Tower)
    cov = tower_coverage(placed, catalog)
    return all(cov.get(c, False) for c in requirements)


def upcoming_coverage_sets(
    catalog: Catalog, from_round: int, to_round: int
) -> tuple[frozenset[CoverageType], ...]:
    """Distinct non-empty coverage requirement sets in [from_round, to_round]."""
    found: set[frozenset[CoverageType]] = set()
    for round_num in range(from_round, to_round + 1):
        round_data = catalog.rounds.get_round_data(round_num)
        if round_data is None:
            continue
        for req, rbe in round_rbe_by_coverage(round_data).items():
            if req and rbe > 1e-9:
                found.add(req)
    return tuple(sorted(found, key=coverage_label))


def unmet_coverage_sets(
    placed: tuple[PlacedTower, ...],
    catalog: Catalog,
    needed: tuple[frozenset[CoverageType], ...],
) -> tuple[frozenset[CoverageType], ...]:
    """Needed sets that no single placed tower currently matches."""
    return tuple(
        req
        for req in needed
        if not any(tower_matches_requirements(t, catalog, req) for t in placed)
    )


def _path_legal_from_tiers(tiers: dict[UpgradePath, int], path: UpgradePath) -> bool:
    current = tiers[path]
    if current >= 5:
        return False
    others = [tiers[p] for p in UpgradePath if p != path]
    if current >= 2 and max(others) >= 3:
        return False
    if current == 0 and sum(t > 0 for t in others) >= 2:
        return False
    return True


def _min_tiers_to_grant_flag(
    placed: PlacedTower,
    catalog: Catalog,
    flag: CoverageType,
) -> int | None:
    """Fewest upgrades on this tower to gain `flag`, or None if crosspath-locked."""
    if tower_coverage(placed, catalog).get(flag, False):
        return 0
    if not isinstance(placed.tower, Tower):
        return None

    best: int | None = None
    base_tiers = {p: int(placed.upgrades[p]) for p in UpgradePath}

    for path in UpgradePath:
        for tier in range(base_tiers[path] + 1, 6):
            upgrade = catalog.upgrades.get_upgrade(placed.tower, path, tier)
            if upgrade is None:
                break
            grants = False
            if flag == CoverageType.CAMO and upgrade.grants_camo:
                grants = True
            if flag == CoverageType.LEAD and upgrade.grants_lead:
                grants = True
            if upgrade.damage_type:
                try:
                    dtype = DamageType(upgrade.damage_type)
                except ValueError:
                    dtype = None
                if dtype is not None and dtype in DAMAGE_TYPE_BY_COVERAGE:
                    if flag in DAMAGE_TYPE_BY_COVERAGE[dtype]:
                        grants = True
            if not grants:
                continue
            # Can we climb `path` to `tier` from the current crosspath?
            state = dict(base_tiers)
            ok = True
            while state[path] < tier:
                if not _path_legal_from_tiers(state, path):
                    ok = False
                    break
                state[path] += 1
            if not ok:
                continue
            steps = tier - base_tiers[path]
            if best is None or steps < best:
                best = steps
            break
    return best


def coverage_unlock_distance(
    placed: tuple[PlacedTower, ...],
    catalog: Catalog,
    req: frozenset[CoverageType],
    *,
    tower_pool: tuple[Tower, ...] = (),
) -> float:
    """Min upgrade steps (plus 1 if a new tower must be placed) to match `req`.

    Returns math.inf if the current board + pool cannot unlock the combo.
    """
    if not req:
        return 0.0
    if any(tower_matches_requirements(t, catalog, req) for t in placed):
        return 0.0

    best = math.inf
    for tower in placed:
        if not isinstance(tower.tower, Tower):
            continue
        steps = 0
        reachable = True
        for flag in req:
            need = _min_tiers_to_grant_flag(tower, catalog, flag)
            if need is None:
                reachable = False
                break
            steps += need
        if reachable:
            best = min(best, float(steps))

    for kind in tower_pool:
        fresh = PlacedTower(tower=kind, position=(0.0, 0.0), ref="_fresh")
        if tower_matches_requirements(fresh, catalog, req):
            best = min(best, 1.0)  # place only
            continue
        steps = 0
        reachable = True
        for flag in req:
            need = _min_tiers_to_grant_flag(fresh, catalog, flag)
            if need is None:
                reachable = False
                break
            steps += need
        if reachable:
            best = min(best, 1.0 + float(steps))

    return best


def total_coverage_unlock_distance(
    placed: tuple[PlacedTower, ...],
    catalog: Catalog,
    needed: tuple[frozenset[CoverageType], ...],
    *,
    tower_pool: tuple[Tower, ...] = (),
) -> float:
    """Sum of unlock distances for every currently unmet needed set."""
    unmet = unmet_coverage_sets(placed, catalog, needed)
    return sum(
        coverage_unlock_distance(placed, catalog, req, tower_pool=tower_pool)
        for req in unmet
    )


def earliest_coverage_round(
    catalog: Catalog,
    req: frozenset[CoverageType],
    from_round: int,
    to_round: int,
) -> int | None:
    """First round in range whose RBE split includes `req`."""
    for round_num in range(from_round, to_round + 1):
        round_data = catalog.rounds.get_round_data(round_num)
        if round_data is None:
            continue
        for key, rbe in round_rbe_by_coverage(round_data).items():
            if key == req and rbe > 1e-9:
                return round_num
    return None


def coverage_prep_urgent(
    catalog: Catalog,
    unmet: tuple[frozenset[CoverageType], ...],
    *,
    current_round: int,
    target_round: int,
    unlock_distance: float,
    horizon: int = 20,
    committed_steps: float = 3.0,
) -> bool:
    """True if we should spend shop actions on coverage unlocks now.

    Far-future combos (Camo+Lead on r59) must not drain cash on r1. Unlock
    when the need is within `horizon` rounds, or we already started the path
    (`unlock_distance` at or below a fresh tower's full climb).
    """
    if not unmet:
        return False
    if unlock_distance <= committed_steps:
        return True
    for req in unmet:
        earliest = earliest_coverage_round(
            catalog, req, current_round, target_round
        )
        if earliest is not None and earliest <= current_round + horizon:
            return True
    return False


def coverage_label(requirements: frozenset[CoverageType]) -> str:
    if not requirements:
        return "any"
    return "+".join(sorted(c.value for c in requirements))


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
    """Estimate DPS from base stats plus per-path upgrade deltas.

    Upgrade rows in the catalog are absolute snapshots for that path/tier
    (often still listing unchanged pierce/damage). Applying them as absolute
    values across crosspaths clobbers other paths (e.g. Quick Shots resets
    Sharp Shots' pierce 3 → 2). So each path contributes only the delta from
    the previous tier on that same path (tier 1 vs base).
    """
    if not isinstance(placed.tower, Tower):
        return 0.0

    data = catalog.towers.get_tower_data(placed.tower)
    if data is None:
        return 0.0

    base_damage = data.damage or 1.0
    base_cooldown = data.cooldown or 1.0
    base_pierce = data.pierce or 1.0
    base_projectiles = data.projectiles or 1.0

    damage = base_damage
    cooldown = base_cooldown
    pierce = base_pierce
    projectiles = base_projectiles

    for path, tier in placed.upgrades.items():
        prev_damage = base_damage
        prev_cooldown = base_cooldown
        prev_pierce = base_pierce
        prev_projectiles = base_projectiles
        for t in range(1, tier + 1):
            upgrade = catalog.upgrades.get_upgrade(placed.tower, path, t)
            if upgrade is None:
                continue
            cur_damage = (
                float(upgrade.damage)
                if upgrade.damage is not None
                else prev_damage
            )
            cur_cooldown = (
                float(upgrade.cooldown)
                if upgrade.cooldown is not None
                else prev_cooldown
            )
            cur_pierce = (
                float(upgrade.pierce)
                if upgrade.pierce is not None
                else prev_pierce
            )
            cur_projectiles = (
                float(upgrade.projectiles)
                if upgrade.projectiles is not None
                else prev_projectiles
            )
            damage += cur_damage - prev_damage
            cooldown += cur_cooldown - prev_cooldown
            pierce += cur_pierce - prev_pierce
            projectiles += cur_projectiles - prev_projectiles
            prev_damage = cur_damage
            prev_cooldown = cur_cooldown
            prev_pierce = cur_pierce
            prev_projectiles = cur_projectiles

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


def effective_dps_for_requirements(
    placed: tuple[PlacedTower, ...],
    track: TrackData,
    catalog: Catalog,
    requirements: frozenset[CoverageType],
) -> float:
    """Path-weighted DPS from towers that can hit this coverage bucket."""
    total = 0.0
    for tower in placed:
        if not tower_matches_requirements(tower, catalog, requirements):
            continue
        total += tower_dps(tower, catalog) * path_fraction_in_range(tower, track, catalog)
    return total


def binding_damage_budget(
    placed: tuple[PlacedTower, ...],
    track: TrackData,
    catalog: Catalog,
    round_data: RoundData,
    transit: float,
) -> tuple[float, float, tuple[TypedBudget, ...], str]:
    """Typed soft-gate scalar comparable to round.rbe.

    RBE is split by required coverage set (camo, lead, purple, black+white,
    camo+lead, …). Each bucket only receives path-weighted DPS from towers
    that match every flag in that set (camo detection and/or damage-type
    coverage). The binding (worst) budget/rbe ratio is scaled back to total
    round RBE so existing planner deficit math keeps working.

    Returns (damage_budget, binding_eff_dps, typed_budgets, detail_fragment).
    """
    buckets = round_rbe_by_coverage(round_data)
    total_rbe = float(round_data.rbe) if round_data.rbe > 0 else 1.0
    typed: list[TypedBudget] = []
    worst_ratio = float("inf")
    worst: TypedBudget | None = None

    for req, bucket_rbe in sorted(
        buckets.items(), key=lambda item: coverage_label(item[0])
    ):
        if bucket_rbe <= 1e-9:
            continue
        eff = effective_dps_for_requirements(placed, track, catalog, req)
        budget = eff * transit
        entry = TypedBudget(
            requirements=req,
            rbe=bucket_rbe,
            effective_dps=eff,
            budget=budget,
        )
        typed.append(entry)
        ratio = budget / bucket_rbe
        if ratio < worst_ratio:
            worst_ratio = ratio
            worst = entry

    if worst is None:
        eff = effective_board_dps(placed, track, catalog)
        return eff * transit, eff, (), "no bloon groups"

    damage_budget = worst_ratio * total_rbe
    parts = [f"{t.label}:{t.budget:.0f}/{t.rbe:.0f}" for t in typed]
    detail = (
        f"binding={worst.label} {worst.budget:.0f}/{worst.rbe:.0f} "
        f"[{', '.join(parts)}]"
    )
    return damage_budget, worst.effective_dps, tuple(typed), detail


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

    Soft gate uses coverage-typed budgets for every interactivity class
    (camo, lead, purple, black, white, and combinations like camo+lead).
    A tower only contributes to a bucket if it matches every required flag
    (camo detection and/or damage-type coverage from the catalog). The
    binding bucket is scaled to total RBE so damage_budget stays comparable
    to rbe * clear_margin.
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

    transit = path_length_units(track) / max(bloon_speed, 1e-6)
    total_eff = effective_board_dps(placed, track, catalog)
    budget, binding_eff, typed, typed_detail = binding_damage_budget(
        placed, track, catalog, round_data, transit
    )

    if missing:
        return RoundVerdict(
            round_num=round_data.round_num,
            status=RoundVerdictStatus.HARD_FAIL,
            rbe=round_data.rbe,
            board_dps=dps,
            effective_dps=binding_eff,
            damage_budget=budget,
            missing=missing,
            typed_budgets=typed,
            detail=f"missing coverage: {', '.join(c.value for c in missing)}",
        )

    required = round_data.rbe * clear_margin
    if budget < required:
        return RoundVerdict(
            round_num=round_data.round_num,
            status=RoundVerdictStatus.SOFT_FAIL,
            rbe=round_data.rbe,
            board_dps=dps,
            effective_dps=binding_eff,
            damage_budget=budget,
            typed_budgets=typed,
            detail=(
                f"budget {budget:.0f} < required {required:.0f} "
                f"(raw_dps={dps:.1f} total_eff={total_eff:.1f} "
                f"transit={transit:.1f}s rbe={round_data.rbe}; {typed_detail})"
            ),
        )

    return RoundVerdict(
        round_num=round_data.round_num,
        status=RoundVerdictStatus.PASS,
        rbe=round_data.rbe,
        board_dps=dps,
        effective_dps=binding_eff,
        damage_budget=budget,
        typed_budgets=typed,
        detail=(
            f"budget {budget:.0f} ok for rbe {round_data.rbe} "
            f"(raw_dps={dps:.1f} total_eff={total_eff:.1f} "
            f"transit={transit:.1f}s; {typed_detail})"
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
