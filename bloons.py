import json
import time
from collections import deque

import cv2

from data.enums import BloonsDifficulty, Tower, BloonsScreen, PAGE_IDENTIFIER_POINTS, MAP_SELECT_PAGE_POINTS, \
    SELECTED_MAP_SELECT_TAB_COLOR, SCREEN_TRANSITIONS, MAP_SELECT_THUMBNAIL_POSITIONS, DIFFICULTY_SELECT_POSITIONS, \
    GAMEMODE_SELECT_POSITIONS, BloonsGamemode
from interaction import WindowManager, InputController
from system_flags import vprint


def color_close(a, b, tol=5):
    return all(abs(a[i] - b[i]) <= tol for i in range(3))


class BloonsBrain:
    def __init__(self, window_title: str = "BloonsTD6"):
        self.window_title = window_title

        # Track data
        self.land_mask = None
        self.water_mask = None
        self.flow_points = None

        # Game data
        self.difficulty: BloonsDifficulty | None = None
        self.gamemode: BloonsGamemode | None = None
        self.game_running: bool = False
        self.selected_map_index: int | None = None

        # Window controller
        self.window_manager = WindowManager(window_title)
        if not self.window_manager.wait_for_window():
            raise RuntimeError(f"Window '{window_title}' not found.")
        self.controller: InputController = self.window_manager.get_relative_controller()

    def load_track_data(self, track_folder_path: str):
        """Load track data for the specified track folder"""
        # Standard paths
        land_mask_path = f"{track_folder_path}/land_placement_mask.png"
        water_mask_path = f"{track_folder_path}/water_placement_mask.png"
        track_json_path = f"{track_folder_path}/path_points.json"

        # Placement masks
        self.land_mask = cv2.imread(land_mask_path)
        if self.land_mask is None:
            raise RuntimeError(f"Could not load land placement mask: '{land_mask_path}'")

        self.water_mask = cv2.imread(water_mask_path)
        if self.water_mask is None:
            raise RuntimeError(f"Could not load water placement mask: '{water_mask_path}'")

        # Flow points
        with open(track_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.flow_points = data.get("flow_points", [])
        if not self.flow_points:
            raise RuntimeError(f"No flow points found in '{track_json_path}'.")

    def set_gamemode(self, gamemode: BloonsGamemode):
        """Set gamemode and difficulty."""
        self.gamemode = gamemode

        # Derive difficulty automatically from GAMEMODE_SELECT_POSITIONS
        for difficulty, gamemode_dict in GAMEMODE_SELECT_POSITIONS.items():
            if gamemode in gamemode_dict:
                self.difficulty = difficulty
                return

        raise ValueError(f"Could not derive difficulty for gamemode: {gamemode}")

    def place_tower(self, tower: Tower):
        if not self.game_running:
            raise RuntimeError("Game is not running.")

        if not self.difficulty:
            raise RuntimeError("Difficulty not set.")

    def identify_current_screen(self) -> tuple[BloonsScreen | None, int | None]:
        # Find the first page where all points match
        capture = self.window_manager.capture_window(force_focus=True)
        for page_name, points in PAGE_IDENTIFIER_POINTS.items():
            found_page = True
            vprint(page_name.value)
            for (w_fraction, h_fraction), color in points:
                point_color = capture.getpixel((int(capture.width * w_fraction), int(capture.height * h_fraction)))
                vprint(point_color, color)
                if not color_close(point_color, color):
                    found_page = False
                    # break
            if found_page:
                if page_name == BloonsScreen.MAP_SELECT:
                    for i, (w_fraction, h_fraction) in enumerate(MAP_SELECT_PAGE_POINTS):
                        point_color = capture.getpixel(
                            (int(capture.width * w_fraction), int(capture.height * h_fraction)))
                        if color_close(point_color, SELECTED_MAP_SELECT_TAB_COLOR):
                            vprint(f"Found page: {page_name} (Tab {i + 1})")
                            return page_name, i + 1
                    vprint("Could not identify selected map tab.")
                    return page_name, None
                else:
                    vprint(f"Found page: {page_name}")
                    return page_name, None

        vprint("Could not identify current screen.")
        return None, None

    @staticmethod
    def _find_path(start: BloonsScreen, goal: BloonsScreen):
        """Find the shortest valid transition path between two screens."""
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

        return None  # No path found

    def _handle_special_transition(self, src: BloonsScreen, dst: BloonsScreen):
        """
        Handle transitions that need custom logic — e.g. entering a game from the map select screen.
        """
        if src == BloonsScreen.MAP_SELECT and dst == BloonsScreen.IN_GAME:
            if not hasattr(self, "selected_map_index") or self.selected_map_index is None:
                raise RuntimeError("No map selected for special transition.")
            if not self.difficulty:
                raise RuntimeError("Difficulty not set.")

            # Select the correct map
            map_index = self.selected_map_index
            if map_index >= len(MAP_SELECT_THUMBNAIL_POSITIONS):
                raise RuntimeError(f"Map index {map_index} out of range.")

            map_pos = MAP_SELECT_THUMBNAIL_POSITIONS[map_index]
            vprint(f"Clicking map {map_index + 1} at {map_pos}")
            self.controller.click(*map_pos)
            time.sleep(0.7)

            # Select difficulty
            diff_pos = DIFFICULTY_SELECT_POSITIONS[self.difficulty]
            vprint(f"Selecting difficulty {self.difficulty.name} at {diff_pos}")
            self.controller.click(*diff_pos)
            time.sleep(0.7)

            # Select gamemode
            gm_pos = GAMEMODE_SELECT_POSITIONS[self.difficulty].get(self.gamemode)
            if gm_pos is None:
                raise RuntimeError(f"Gamemode {self.gamemode} not valid for {self.difficulty.name}.")
            vprint(f"Selecting gamemode {self.gamemode} at {gm_pos}")
            self.controller.click(*gm_pos)
            time.sleep(0.7)
            return True

        raise RuntimeError(f"No special handler for {src} → {dst}")

    def navigate_to(self, target: BloonsScreen):
        current_screen, tab = self.identify_current_screen()
        if current_screen is None:
            raise RuntimeError("Could not identify current screen.")
        if current_screen == target:
            return

        path = self._find_path(current_screen, target)
        if not path:
            raise RuntimeError(f"Could not find path from {current_screen} to {target}.")

        for i in range(len(path) - 1):
            src, dst = path[i], path[i + 1]
            transition = SCREEN_TRANSITIONS[src][dst]
            action = transition["action"]

            vprint(f"{src.name} → {dst.name}")

            if action == "click":
                x, y = transition["pos"]
                self.controller.click(x, y, force_focus=True)

            elif action == "key":
                self.controller.press_key(transition["key"])

            elif action == "special":
                self._handle_special_transition(src, dst)

            else:
                raise ValueError(f"Unknown action type: {action}")

            # Wait for the next screen to appear (10 second timeout)
            timeout = 10
            start_time = time.time()
            new_screen = None
            while time.time() - start_time < timeout:
                new_screen, _ = self.identify_current_screen()
                if new_screen == dst:
                    break
                time.sleep(0.5)

            if new_screen != dst:
                print(f"Timeout: Expected {dst.name}, but got {new_screen}")
                return False

        vprint(f"Reached {target.name}")
        return True


def main():
    brain = BloonsBrain()

    # Load data for Monkey Meadow
    brain.load_track_data("data/tracks/monkey_meadow")

    # Update gamemode
    brain.set_gamemode(BloonsGamemode.DOUBLE_HP_MOABS)
    brain.selected_map_index = 0

    brain.navigate_to(BloonsScreen.RESTART_POPUP)


if __name__ == "__main__":
    main()
