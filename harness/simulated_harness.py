from dataclasses import replace
import uuid

from actions import Action, PlaceHero, PlaceTower, StartRound, Upgrade, Wait
from catalog import Catalog
from data.enums import BloonsScreen, Hero, Tower, Track
from data.track_data import TrackData
from harness import Harness
from observation import (
    Believed,
    Forecast,
    GameSetup,
    Observation,
    PlacedTower,
    PlacementCandidate,
    Sensed,
    StepResult,
)
from system_flags import PIXELS_PER_BLOONS_UNIT, vprint


class SimulatedHarness(Harness):
    def __init__(self):
        super().__init__()
        self._catalog = Catalog()
        self._setup: GameSetup | None = None
        self._round_index: int = 0
        self._cash: float = 0.0
        self._placed: list[PlacedTower] = []
        self._hero_placed: bool = False
        self._last_step_ok: bool = True
        self._play_idle: bool = True
        self._screen: BloonsScreen = BloonsScreen.IN_GAME
        self._track_data: TrackData | None = None
        self._occupied_mask = None

    def reset(self, setup: GameSetup) -> Observation:
        if self._catalog.heroes.get_hero_data(setup.hero) is None:
            raise ValueError(f"Unknown hero '{setup.hero.value}'")

        self._setup = setup
        self._placed = []
        self._hero_placed = False
        self._last_step_ok = True
        self._play_idle = True
        self._cash = self._catalog.starting_cash(setup.gamemode)
        self._round_index = self._catalog.starting_round(setup.gamemode)
        self._select_track(setup.track)
        self._screen = BloonsScreen.IN_GAME

        vprint(
            f"[sim] Reset {setup.track.value} / {setup.gamemode.value} / {setup.hero.value} "
            f"(round {self._round_index}, ${self._cash})"
        )
        return self.observe()

    def observe(self) -> Observation:
        setup = self._require_setup()
        sensed = Sensed(
            screen=self._screen,
            play_idle=self._play_idle,
            last_step_ok=self._last_step_ok,
        )
        believed = Believed(
            track=setup.track,
            gamemode=setup.gamemode,
            hero=setup.hero,
            round_index=self._round_index,
            cash=self._cash,
            placed=tuple(self._placed),
            hero_placed=self._hero_placed,
        )
        forecast = Forecast(
            remaining=self._catalog.remaining_rounds(self._round_index)
        )
        return Observation(sensed=sensed, believed=believed, forecast=forecast)

    def step(self, action: Action) -> StepResult:
        try:
            return self._step(action)
        except Exception as e:
            self._last_step_ok = False
            vprint(f"[sim] step() caught {type(e).__name__}: {e}")
            if self._setup is None:
                raise
            return StepResult(ok=False, observation=self.observe(), error=str(e))

    def placement_candidates(self, tower: Tower | Hero) -> list[PlacementCandidate]:
        raise NotImplementedError

    def _step(self, action: Action) -> StepResult:
        self._require_setup()
        if isinstance(action, StartRound):
            return self._step_start_round()
        if isinstance(action, Wait):
            return self._step_wait()
        if isinstance(action, PlaceTower):
            return self._step_place_tower(action)
        if isinstance(action, PlaceHero):
            return self._step_place_hero(action)
        if isinstance(action, Upgrade):
            return self._step_upgrade(action)
        return self._fail("unhandled_action")

    def _ok(self, placed_id: uuid.UUID | None = None) -> StepResult:
        self._last_step_ok = True
        return StepResult(ok=True, observation=self.observe(), placed_id=placed_id)

    def _fail(self, error: str) -> StepResult:
        self._last_step_ok = False
        vprint(f"[sim] step failed: {error}")
        return StepResult(ok=False, observation=self.observe(), error=error)

    def _shop_error(self) -> str | None:
        if self._screen != BloonsScreen.IN_GAME:
            return "not_in_game"
        if not self._play_idle:
            return "not_idle"
        return None

    def _step_wait(self) -> StepResult:
        err = self._shop_error()
        if err:
            return self._fail(err)
        return self._ok()

    def _step_start_round(self) -> StepResult:
        setup = self._require_setup()
        if self._screen != BloonsScreen.IN_GAME:
            return self._fail("not_in_game")
        if not self._play_idle:
            return self._fail("not_idle")

        income = self._catalog.income_for_round(self._round_index, setup.gamemode)
        if income is None:
            return self._fail("unknown_round")

        # Instant clock: round completes immediately.
        self._cash += income
        finished = self._round_index
        self._round_index += 1
        self._play_idle = True
        vprint(
            f"[sim] Round {finished} done (+${income} -> ${self._cash}, "
            f"next {self._round_index})"
        )
        return self._ok()

    def _step_place_tower(self, action: PlaceTower) -> StepResult:
        setup = self._require_setup()
        err = self._shop_error()
        if err:
            return self._fail(err)
        if self._track_data is None:
            return self._fail("no_track")
        if self._ref_taken(action.ref):
            return self._fail("duplicate_ref")
        cost = self._catalog.cost_place(action.tower, setup.difficulty)
        if self._cash < cost:
            return self._fail("cannot_afford")

        placed = self._commit_place(action.tower, action.position, cost, action.ref)
        vprint(
            f"[sim] Placed {action.tower.value} ({action.ref}) at {action.position} "
            f"for ${cost}/{self._cash}"
        )
        return self._ok(placed_id=placed.id)

    def _step_place_hero(self, action: PlaceHero) -> StepResult:
        setup = self._require_setup()
        err = self._shop_error()
        if err:
            return self._fail(err)
        if self._track_data is None:
            return self._fail("no_track")
        if self._hero_placed:
            return self._fail("hero_already_placed")
        if self._ref_taken(action.ref):
            return self._fail("duplicate_ref")
        cost = self._catalog.cost_place(setup.hero, setup.difficulty)
        if self._cash < cost:
            return self._fail("cannot_afford")

        placed = self._commit_place(setup.hero, action.position, cost, action.ref)
        self._hero_placed = True
        vprint(
            f"[sim] Placed hero {setup.hero} ({action.ref}) at {action.position} "
            f"for ${cost}/{self._cash}"
        )
        return self._ok(placed_id=placed.id)

    def _step_upgrade(self, action: Upgrade) -> StepResult:
        setup = self._require_setup()
        err = self._shop_error()
        if err:
            return self._fail(err)
        try:
            idx, placed = self._placed_by_ref(action.ref)
        except KeyError:
            return self._fail("unknown_tower")
        if not isinstance(placed.tower, Tower):
            return self._fail("upgrading_hero")
        if action.upgrade_path not in self._catalog.legal_upgrades(placed):
            return self._fail("illegal_upgrade")
        cost = self._catalog.cost_upgrade(placed, action.upgrade_path, setup.difficulty)
        if self._cash < cost:
            return self._fail("cannot_afford")

        upgrade = self._catalog.upgrades.get_next_upgrade(
            placed.tower, action.upgrade_path, placed.upgrades[action.upgrade_path]
        )
        name = upgrade.name if upgrade is not None else action.upgrade_path.value
        self._spend(cost)
        new_upgrades = dict(placed.upgrades)
        new_upgrades[action.upgrade_path] = new_upgrades[action.upgrade_path] + 1
        self._placed[idx] = replace(placed, upgrades=new_upgrades)
        vprint(
            f"[sim] Upgraded {placed.ref} ({placed.tower}) with {name} "
            f"({action.upgrade_path.value} -> {new_upgrades[action.upgrade_path]}) "
            f"for ${cost}/{self._cash}"
        )
        return self._ok()

    def _commit_place(
        self,
        kind: Tower | Hero,
        position: tuple[float, float],
        cost: float,
        ref: str,
    ) -> PlacedTower:
        radius_px = self._footprint_radius_px(kind)
        self._spend(cost)
        placed = PlacedTower(tower=kind, position=position, ref=ref, radius_px=radius_px)
        self._placed.append(placed)
        self._mark_occupied(position, radius_px)
        return placed

    def _select_track(self, track: Track) -> None:
        data = self._catalog.tracks.get_track_data(track)
        if data is None:
            raise RuntimeError(f"No track data for '{track.value}'")
        self._track_data = data
        self._occupied_mask = data.empty_occupancy()

    def _require_setup(self) -> GameSetup:
        if self._setup is None:
            raise RuntimeError("SimulatedHarness has no GameSetup; call reset() first.")
        return self._setup

    def _ref_taken(self, ref: str) -> bool:
        return any(placed.ref == ref for placed in self._placed)

    def _placed_by_ref(self, ref: str) -> tuple[int, PlacedTower]:
        for i, placed in enumerate(self._placed):
            if placed.ref == ref:
                return i, placed
        raise KeyError(f"No placed tower with ref '{ref}'")

    def _footprint_radius_px(self, kind: Tower | Hero) -> int:
        if isinstance(kind, Tower):
            data = self._catalog.towers.get_tower_data(kind)
        else:
            data = self._catalog.heroes.get_hero_data(kind)
        if data is None:
            raise KeyError(f"No catalog entry for {kind}")

        if data.footprint_shape == "circular":
            return int((data.footprint_radius or 10) * PIXELS_PER_BLOONS_UNIT)
        if data.footprint_shape == "rectangular":
            width = getattr(data, "footprint_width", None) or 10
            height = getattr(data, "footprint_height", None) or 10
            radius = (width ** 2 + height ** 2) ** 0.5 / 2
            return int(radius * PIXELS_PER_BLOONS_UNIT)
        return int(10 * PIXELS_PER_BLOONS_UNIT)

    def _mark_occupied(self, position: tuple[float, float], radius_px: int) -> None:
        from data.masks import stamp_disk
        if self._track_data is None:
            return

        h, w = self._track_data.size
        px = int(position[0] * w)
        py = int(position[1] * h)
        stamp_disk(self._occupied_mask, px, py, int(radius_px * 1.5)) # type: ignore

    def _spend(self, amount: float) -> None:
        self._cash = max(self._cash - amount, 0.0)
