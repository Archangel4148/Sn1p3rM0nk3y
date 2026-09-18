import json

from actions import Action
from data.enums import Track
from harness import Harness
from interaction import InputController, WindowManager
from observation import PlacedTower, GameSetup, Observation, StepResult, Sensed, Forecast, Believed
from catalog import Catalog
import cv2
import numpy as np

class GameHarness(Harness):
    # Harness for a BTD6 game window

    def __init__(self):
        super().__init__()

        # Database + window/input management
        self._catalog = Catalog()
        self._window_manager = WindowManager("BloonsTD6")

        # Tracking state
        self._setup: GameSetup | None = None
        self._round_index: int = 0
        self._cash: float = 0.0
        self._placed: list[PlacedTower] = []
        self._hero_placed: bool = False

        # Internal state (never exposed)
        self._controller: InputController = self._window_manager.get_relative_controller()
        self._track_mask: np.ndarray | None = None
        self._land_mask: np.ndarray | None = None
        self._water_mask: np.ndarray | None = None
        self._occupied_mask: np.ndarray | None = None
        self._flow_points: list[list[float]] | None = None
        self._selected_track: Track | None = None
         
    def reset(self, setup: GameSetup) -> Observation:
        raise NotImplementedError

    def observe(self) -> Observation:

        sensed = Sensed(
            screen=None,
            play_idle=None,
            last_step_ok=None
        )
        believed = Believed(
            track=self._setup.track,
            gamemode=self._setup.gamemode,
            hero=self._setup.hero,
            round_index=self._round_index,
            cash=self._cash,
            placed=self._placed,
            hero_placed=self._hero_placed
        )
        forecast = Forecast(
            remaining=self._catalog.remaining_rounds(self._round_index)
        )

        return Observation(
            sensed=sensed,
            believed=believed,
            forecast=forecast,
        )

    def step(self, action: Action) -> StepResult:
        raise NotImplementedError

    def select_track(self, track: Track):
        """Load track data for the specified track folder"""
        # Standard paths
        track_folder_path = f"data/tracks/{track.value.lower().replace(' ', '_')}"
        track_mask_path = f"{track_folder_path}/track_mask.png"
        land_mask_path = f"{track_folder_path}/land_placement_mask.png"
        water_mask_path = f"{track_folder_path}/water_placement_mask.png"
        track_json_path = f"{track_folder_path}/path_points.json"

        # Track mask
        self._track_mask = cv2.imread(track_mask_path)
        if self._track_mask is None:
            raise RuntimeError(f"Could not load track mask: '{track_mask_path}'")

        # Placement masks
        self._land_mask = cv2.imread(land_mask_path)
        if self._land_mask is None:
            raise RuntimeError(f"Could not load land placement mask: '{land_mask_path}'")

        self._water_mask = cv2.imread(water_mask_path)
        if self._water_mask is None:
            raise RuntimeError(f"Could not load water placement mask: '{water_mask_path}'")

        # Occupied spaces mask
        self._occupied_mask = np.zeros_like(self.land_mask[:, :, 0], dtype=np.uint8)

        # Flow points
        with open(track_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._flow_points = data.get("flow_points", [])
        if not self._flow_points:
            raise RuntimeError(f"No flow points found in '{track_json_path}'.")

        self._selected_track = track


    ###### INTEGRATION IN PROGRESS ######

    def navigate_to(self, target: BloonsScreen):
        current_screen = identify_screen(self.window_manager.capture_window(force_focus=True))
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
                self.controller.click(x, y, force_focus=True)

            elif action == "key":
                self.controller.press_key(transition["key"])

            elif action == "custom":
                self._handle_special_transition(src, dst)

            else:
                raise ValueError(f"Unknown action type: {action}")

            time.sleep(post_delay)

            if not self.wait_for_screen(dst):
                current_screen = identify_screen(self.window_manager.capture_window(force_focus=True))
                print(f"Timeout: Expected {dst.name}, but got {current_screen}")
                return False

        vprint(f"Reached {target.name}")
        return True

    ############## TOWER PLACEMENT ##############

    def place_tower(self, tower: Tower, position: tuple[float, float]):
        current_screen = identify_screen(self.window_manager.capture_window(force_focus=True))
        if current_screen not in (BloonsScreen.IN_GAME, BloonsScreen.SANDBOX_MONKEY_SCREEN):
            raise RuntimeError("Game is not running.")

        # Convert normalized position → pixel coordinates
        h, w = self.land_mask.shape[:2]
        px = int(position[0] * w)
        py = int(position[1] * h)
        radius_px = self.get_tower_radius_px(tower)

        # Select and place
        self.controller.press_key(TOWER_HOTKEYS[tower])
        self.controller.click(*position)

        cost = self.get_tower_cost(tower)
        vprint(f"Placed tower {len(self.placed_towers)}: {tower.value} at {position} for ${cost}/{self.money}")
        self.update_money_estimate(-cost)

        # Record tower info and mark occupied region
        placed = PlacedTower(
            tower=tower,
            position=position,
            radius_px=radius_px,
        )
        self.placed_towers.append(placed)
        cv2.circle(self.occupied_mask, (px, py), int(radius_px * 1.5), 255, -1)

    def place_hero(self, position: tuple[float, float]):
        if self.selected_hero is None:
            raise RuntimeError("No hero selected.")
        if self.hero_placed:
            vprint("Hero already placed.")
            return

        info = self.get_tower_info(self.selected_hero)
        h, w = self.land_mask.shape[:2]
        px = int(position[0] * w)
        py = int(position[1] * h)
        radius_px = int(info["footprint_radius"] * PIXELS_PER_BLOONS_UNIT)

        self.controller.press_key("p")
        self.controller.click(*position)

        cost = self.get_tower_cost(self.selected_hero)
        vprint(f"Placed hero {self.selected_hero} at {position} for ${cost}/{self.money}")
        self.update_money_estimate(-cost)

        # Mark occupied space
        cv2.circle(self.occupied_mask, (px, py), int(radius_px * 1.5), 255, -1)
        self.hero_placed = True