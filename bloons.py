import json
from enum import IntEnum

import cv2

from interaction import WindowManager, InputController


class BloonsDifficulty(IntEnum):
    EASY = 0
    MEDIUM = 1
    HARD = 2
    IMPOPPABLE = 3


class BloonsBrain:
    def __init__(self, window_title: str = "BloonsTD6"):
        self.window_title = window_title

        # Track data
        self.land_mask = None
        self.water_mask = None
        self.flow_points = None

        # Game data
        self.difficulty = None

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

    def set_difficulty(self, difficulty: BloonsDifficulty):
        self.difficulty = difficulty


def main():
    brain = BloonsBrain()

    # Load data for Monkey Meadow
    brain.load_track_data("data/tracks/monkey_meadow")

    # Update game difficulty
    brain.set_difficulty(BloonsDifficulty.MEDIUM)


if __name__ == "__main__":
    main()
