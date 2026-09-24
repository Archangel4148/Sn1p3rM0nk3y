from collections import deque
from dataclasses import replace
import time
import uuid

from actions import Action, PlaceHero, PlaceTower, StartRound, Upgrade, Wait
from catalog import Catalog
from data.enums import (
    BloonsGamemode,
    BloonsScreen,
    DIFFICULTY_SELECT_POSITIONS,
    GAMEMODE_SELECT_POSITIONS,
    Hero,
    MAP_SELECT_LEFT_ARROW_POSITION,
    MAP_SELECT_RIGHT_ARROW_POSITION,
    MAP_SELECT_THUMBNAIL_POSITIONS,
    PLAY_BUTTON_POSITION,
    SCREEN_TRANSITIONS,
    TOWER_HOTKEYS,
    TRACK_THUMBNAIL_LOCATIONS,
    Track,
    Tower,
    UPGRADE_HOTKEYS,
)
from data.track_data import TrackData
from harness import Harness
from harness.placement import find_placement_candidates
from interaction import InputController, WindowManager
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
from system_flags import PIXELS_PER_BLOONS_UNIT, UPGRADE_DELAY, vprint
from vision import get_current_tab, identify_screen

class GameHarness(Harness):
    # Harness for a BTD6 game window

    def __init__(self):
        super().__init__()

        self._catalog = Catalog()
        self._window_manager = WindowManager("BloonsTD6")
        if not self._window_manager.wait_for_window():
            raise RuntimeError("Window 'BloonsTD6' not found.")
        self._controller: InputController = self._window_manager.get_relative_controller()

        self._setup: GameSetup | None = None
        self._round_index: int = 0
        self._cash: float = 0.0
        self._placed: list[PlacedTower] = []
        self._hero_placed: bool = False
        self._last_step_ok: bool = True

        self._track_data: TrackData | None = None
        self._occupied_mask = None

    def reset(self, setup: GameSetup) -> Observation:
        """Clear the harness state, and set up for the next execution"""
        if self._catalog.heroes.get_hero_data(setup.hero) is None:
            raise ValueError(f"Unknown hero '{setup.hero.value}'")

        # Clear state
        self._setup = setup
        self._placed = []
        self._hero_placed = False
        self._last_step_ok = True
        self._cash = self._catalog.starting_cash(setup.gamemode)
        self._round_index = self._catalog.starting_round(setup.gamemode)
        self.select_track(setup.track)

        # Return to the main menu, then navigate to the target screen
        self._window_manager.focus_window()
        self._ensure_screen(BloonsScreen.MAIN_MENU)
        self._ensure_screen(self._in_game_screen(setup.gamemode))

        vprint(
            f"Reset {setup.track.value} / {setup.gamemode.value} / {setup.hero.value} "
            f"(round {self._round_index}, ${self._cash})"
        )
        return self.observe()

    @staticmethod
    def _in_game_screen(gamemode: BloonsGamemode) -> BloonsScreen:
        if gamemode in (
            BloonsGamemode.EASY_SANDBOX,
            BloonsGamemode.MEDIUM_SANDBOX,
            BloonsGamemode.HARD_SANDBOX,
        ):
            return BloonsScreen.SANDBOX_MONKEY_SCREEN
        return BloonsScreen.IN_GAME

    def _current_screen(self) -> BloonsScreen | None:
        capture = self._window_manager.capture_window(force_focus=True)
        if capture is None:
            return None
        return identify_screen(capture)

    def _ensure_screen(self, target: BloonsScreen) -> None:
        if self._current_screen() == target:
            return
        self.navigate_to(target)
        if not self.wait_for_screen(target, timeout=15.0):
            raise RuntimeError(f"reset() failed to reach {target.value}")

    def observe(self) -> Observation:
        if self._setup is None:
            raise RuntimeError("GameHarness.observe() called before reset().")

        capture = self._window_manager.capture_window(force_focus=False)
        screen = identify_screen(capture) if capture is not None else None

        sensed = Sensed(
            screen=screen,
            play_idle=self._is_play_idle(capture),
            last_step_ok=self._last_step_ok,
        )
        believed = Believed(
            track=self._setup.track,
            gamemode=self._setup.gamemode,
            hero=self._setup.hero,
            round_index=self._round_index,
            cash=self._cash,
            placed=tuple(self._placed),
            hero_placed=self._hero_placed,
        )
        forecast = Forecast(
            remaining=self._catalog.remaining_rounds(self._round_index)
        )
        return Observation(sensed=sensed, believed=believed, forecast=forecast)

    def placement_candidates(self, tower: Tower | Hero) -> list[PlacementCandidate]:
        if self._track_data is None or self._occupied_mask is None:
            raise RuntimeError("No track loaded; call reset() first.")
        return find_placement_candidates(
            self._catalog,
            self._track_data,
            self._occupied_mask,
            tower,
        )

    def step(self, action: Action) -> StepResult:
        try:
            return self._step(action)
        except Exception as e:
            self._last_step_ok = False
            vprint(f"step() caught {type(e).__name__}: {e}")
            if self._setup is None:
                raise
            return StepResult(ok=False, observation=self.observe(), error=str(e))

    def _step(self, action: Action) -> StepResult:
        self._require_setup()
        capture = self._window_manager.capture_window(force_focus=True)

        if isinstance(action, StartRound):
            return self._step_start_round(capture)
        if isinstance(action, Wait):
            return self._step_wait(capture)
        if isinstance(action, PlaceTower):
            return self._step_place_tower(action, capture)
        if isinstance(action, PlaceHero):
            return self._step_place_hero(action, capture)
        if isinstance(action, Upgrade):
            return self._step_upgrade(action, capture)
        return self._fail("unhandled_action")

    def _ok(self, placed_id: uuid.UUID | None = None) -> StepResult:
        self._last_step_ok = True
        return StepResult(ok=True, observation=self.observe(), placed_id=placed_id)

    def _fail(self, error: str) -> StepResult:
        self._last_step_ok = False
        vprint(f"step failed: {error}")
        return StepResult(ok=False, observation=self.observe(), error=error)

    def _shop_error(self, capture) -> str | None:
        if capture is None:
            return "no_capture"
        screen = identify_screen(capture)
        if screen not in (BloonsScreen.IN_GAME, BloonsScreen.SANDBOX_MONKEY_SCREEN):
            return "not_in_game"
        if not self._is_play_idle(capture):
            return "not_idle"
        return None

    def _step_wait(self, capture) -> StepResult:
        err = self._shop_error(capture)
        if err:
            return self._fail(err)
        return self._ok()

    def _step_start_round(self, capture) -> StepResult:
        setup = self._require_setup()
        if capture is None:
            return self._fail("no_capture")
        screen = identify_screen(capture)
        if screen not in (BloonsScreen.IN_GAME, BloonsScreen.SANDBOX_MONKEY_SCREEN):
            return self._fail("not_in_game")
        if not self._is_play_idle(capture):
            return self._fail("not_idle")

        income = self._catalog.income_for_round(self._round_index, setup.gamemode)
        if income is None:
            return self._fail("unknown_round")

        self._controller.click(*PLAY_BUTTON_POSITION, force_focus=True)
        if not self._wait_for_round_end():
            return self._fail("round_timeout")

        self._cash += income
        finished = self._round_index
        self._round_index += 1
        vprint(f"Round {finished} done (+${income} -> ${self._cash}, next {self._round_index})")
        return self._ok()

    def _wait_for_round_end(self, timeout: float = 300.0, interval: float = 0.25) -> bool:
        deadline = time.time() + timeout
        saw_running = False
        while time.time() < deadline:
            capture = self._window_manager.capture_window(force_focus=False)
            if not self._is_play_idle(capture):
                saw_running = True
            elif saw_running:
                return True
            time.sleep(interval)
        return False

    def _step_place_tower(self, action: PlaceTower, capture) -> StepResult:
        setup = self._require_setup()
        err = self._shop_error(capture)
        if err:
            return self._fail(err)
        if self._track_data is None:
            return self._fail("no_track")
        if self._ref_taken(action.ref):
            return self._fail("duplicate_ref")
        cost = self._catalog.cost_place(action.tower, setup.difficulty)
        if self._cash < cost:
            return self._fail("cannot_afford")

        placed = self._place(action.tower, action.position, cost, action.ref)
        vprint(
            f"Placed {action.tower.value} ({action.ref}) at {action.position} "
            f"for ${cost}/{self._cash}"
        )
        return self._ok(placed_id=placed.id)

    def _step_place_hero(self, action: PlaceHero, capture) -> StepResult:
        setup = self._require_setup()
        err = self._shop_error(capture)
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

        placed = self._place(setup.hero, action.position, cost, action.ref, hotkey="p")
        self._hero_placed = True
        vprint(
            f"Placed hero {setup.hero} ({action.ref}) at {action.position} "
            f"for ${cost}/{self._cash}"
        )
        return self._ok(placed_id=placed.id)

    def _step_upgrade(self, action: Upgrade, capture) -> StepResult:
        setup = self._require_setup()
        err = self._shop_error(capture)
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

        self._controller.click(*placed.position)
        time.sleep(UPGRADE_DELAY)
        self._controller.press_key(UPGRADE_HOTKEYS[action.upgrade_path.value])
        time.sleep(0.1)
        self._controller.click(*placed.position)

        upgrade = self._catalog.upgrades.get_next_upgrade(
            placed.tower, action.upgrade_path, placed.upgrades[action.upgrade_path]
        )
        name = upgrade.name if upgrade is not None else action.upgrade_path.value
        self._spend(cost)
        new_upgrades = dict(placed.upgrades)
        new_upgrades[action.upgrade_path] = new_upgrades[action.upgrade_path] + 1
        self._placed[idx] = replace(placed, upgrades=new_upgrades)
        vprint(
            f"Upgraded {placed.ref} ({placed.tower}) with {name} "
            f"({action.upgrade_path.value} -> {new_upgrades[action.upgrade_path]}) "
            f"for ${cost}/{self._cash}"
        )
        return self._ok()

    def _place(
        self,
        kind: Tower | Hero,
        position: tuple[float, float],
        cost: float,
        ref: str,
        hotkey: str | None = None,
    ) -> PlacedTower:
        if hotkey is not None:
            key = hotkey
        elif isinstance(kind, Tower):
            key = TOWER_HOTKEYS[kind]
        else:
            raise TypeError(f"No hotkey for {kind}")
        radius_px = self._footprint_radius_px(kind)
        self._controller.press_key(key)
        self._controller.click(*position)
        self._spend(cost)
        placed = PlacedTower(tower=kind, position=position, ref=ref, radius_px=radius_px)
        self._placed.append(placed)
        self._mark_occupied(position, radius_px)
        return placed

    def _ref_taken(self, ref: str) -> bool:
        return any(placed.ref == ref for placed in self._placed)

    def _mark_occupied(self, position: tuple[float, float], radius_px: int) -> None:
        from data.masks import stamp_disk

        h, w = self._track_data.size
        px = int(position[0] * w)
        py = int(position[1] * h)
        stamp_disk(self._occupied_mask, px, py, int(radius_px * 1.5))

    def _is_play_idle(self, capture) -> bool:
        # TODO: play-triangle vs fast-forward pixel.
        return False

    def select_track(self, track: Track):
        data = self._catalog.tracks.get_track_data(track)
        if data is None:
            raise RuntimeError(f"No track data for '{track.value}'")
        self._track_data = data
        self._occupied_mask = data.empty_occupancy()

    def _require_setup(self) -> GameSetup:
        if self._setup is None:
            raise RuntimeError("GameHarness has no GameSetup; call reset() first.")
        return self._setup

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

    def _spend(self, amount: float) -> None:
        self._cash = max(self._cash - amount, 0.0)

    def wait_for_screen(self, target: BloonsScreen, timeout: float = 10.0, interval: float = 0.5) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_screen = identify_screen(self._window_manager.capture_window(force_focus=True))
            if current_screen == target:
                return True
            time.sleep(interval)
        return False

    @staticmethod
    def _find_path(start: BloonsScreen, goal: BloonsScreen):
        visited = set()
        queue = deque([(start, [start])])

        while queue:
            current, path = queue.popleft()
            if current == goal:
                return path

            visited.add(current)
            if current not in SCREEN_TRANSITIONS:
                continue

            for next_screen in SCREEN_TRANSITIONS[current]:
                if next_screen not in visited:
                    queue.append((next_screen, path + [next_screen]))
        return None

    def _handle_special_transition(self, src: BloonsScreen, dst: BloonsScreen):
        setup = self._require_setup()
        if src == BloonsScreen.MAP_SELECT and dst in (BloonsScreen.IN_GAME, BloonsScreen.SANDBOX_START_POPUP):
            current_tab = get_current_tab(self._window_manager.capture_window(force_focus=True))
            if current_tab is None:
                raise RuntimeError("Could not identify the map-select tab.")
            current_tab_idx = current_tab - 1

            target_page_idx, thumbnail_index = TRACK_THUMBNAIL_LOCATIONS[setup.track]

            for _ in range(abs(target_page_idx - current_tab_idx)):
                if target_page_idx > current_tab_idx:
                    self._controller.click(*MAP_SELECT_RIGHT_ARROW_POSITION, duration=0.05)
                else:
                    self._controller.click(*MAP_SELECT_LEFT_ARROW_POSITION, duration=0.05)

            if thumbnail_index >= len(MAP_SELECT_THUMBNAIL_POSITIONS):
                raise RuntimeError(f"Map index {thumbnail_index} out of range.")
            map_pos = MAP_SELECT_THUMBNAIL_POSITIONS[thumbnail_index]
            vprint(f"Clicking map at position {thumbnail_index + 1} ({map_pos})")
            self._controller.click(*map_pos)
            time.sleep(0.2)

            diff_pos = DIFFICULTY_SELECT_POSITIONS[setup.difficulty]
            vprint(f"Selecting difficulty {setup.difficulty.name} at {diff_pos}")
            self._controller.click(*diff_pos)
            time.sleep(0.2)

            gm_pos = GAMEMODE_SELECT_POSITIONS[setup.difficulty].get(setup.gamemode)
            if gm_pos is None:
                raise RuntimeError(f"Gamemode {setup.gamemode} not valid for {setup.difficulty.name}.")
            vprint(f"Selecting gamemode {setup.gamemode} at {gm_pos}")
            self._controller.click(*gm_pos)
            return True
        raise RuntimeError(f"No special handler for {src} → {dst}")

    def navigate_to(self, target: BloonsScreen):
        current_screen = identify_screen(self._window_manager.capture_window(force_focus=True))
        if current_screen is None:
            raise RuntimeError("Could not identify current screen.")
        if current_screen == target:
            return False

        path = self._find_path(current_screen, target)
        if not path:
            raise RuntimeError(f"Could not find path from {current_screen} to {target}.")

        for i in range(len(path) - 1):
            src, dst = path[i], path[i + 1]
            transition = SCREEN_TRANSITIONS[src][dst]
            action = transition["action"]
            delay = transition.get("delay", 0)
            post_delay = transition.get("post_delay", 0)
            time.sleep(delay)
            vprint(f"{src.name} → {dst.name}")

            if action == "click":
                x, y = transition["pos"]
                self._controller.click(x, y, force_focus=True)

            elif action == "key":
                self._controller.press_key(transition["key"])

            elif action == "custom":
                self._handle_special_transition(src, dst)

            else:
                raise ValueError(f"Unknown action type: {action}")

            time.sleep(post_delay)

            if not self.wait_for_screen(dst):
                current_screen = identify_screen(self._window_manager.capture_window(force_focus=True))
                print(f"Timeout: Expected {dst.name}, but got {current_screen}")
                return False

        vprint(f"Reached {target.name}")
        return True

    def _placed_by_ref(self, ref: str) -> tuple[int, PlacedTower]:
        for i, placed in enumerate(self._placed):
            if placed.ref == ref:
                return i, placed
        raise KeyError(f"No placed tower with ref '{ref}'")

    def _placement_mask(self, kind: Tower | Hero):
        if self._track_data is None:
            raise RuntimeError("No track loaded.")
        if isinstance(kind, Tower):
            data = self._catalog.towers.get_tower_data(kind)
        else:
            data = self._catalog.heroes.get_hero_data(kind)
        if data is None:
            raise KeyError(f"No catalog entry for {kind}")

        if data.placement_type == "land":
            return self._track_data.land_mask
        if data.placement_type == "water":
            return self._track_data.water_mask
        if data.placement_type == "any":
            from data.masks import mask_or

            return mask_or(self._track_data.land_mask, self._track_data.water_mask)
        raise ValueError(f"Unknown placement type: {data.placement_type}")

    @staticmethod
    def _is_valid_terrain(mask, x: int, y: int) -> bool:
        return bool(mask[y, x] >= 128)

    def _intersects_track(self, x: int, y: int, radius: int, w: int, h: int) -> bool:
        import numpy as np
        y0, y1 = max(y - radius, 0), min(y + radius, h)
        x0, x1 = max(x - radius, 0), min(x + radius, w)
        return bool(np.any(self._track_data.track_mask[y0:y1, x0:x1] > 128))

    def _overlaps_existing_tower(self, x: int, y: int, radius: int, w: int, h: int) -> bool:
        import numpy as np
        y0, y1 = max(y - radius, 0), min(y + radius, h)
        x0, x1 = max(x - radius, 0), min(x + radius, w)
        return bool(np.any(self._occupied_mask[y0:y1, x0:x1] > 0))

    def can_place_tower_on_map(self, kind: Tower | Hero, sample_step: int = 20) -> bool:
        mask = self._placement_mask(kind)
        tower_radius = self._footprint_radius_px(kind)
        h, w = mask.shape[:2]

        for y in range(0, h, sample_step):
            for x in range(0, w, sample_step):
                if mask[y, x] < 128:
                    continue
                if self._intersects_track(x, y, tower_radius, w, h):
                    continue
                return True
        return False

