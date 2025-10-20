import json
import time
from collections import deque
from dataclasses import dataclass, field

import cv2
import numpy as np

from data.enums import BloonsDifficulty, BloonsScreen, SCREEN_TRANSITIONS, MAP_SELECT_THUMBNAIL_POSITIONS, \
    DIFFICULTY_SELECT_POSITIONS, GAMEMODE_SELECT_POSITIONS, BloonsGamemode, Track, TRACK_THUMBNAIL_LOCATIONS, \
    MAP_SELECT_RIGHT_ARROW_POSITION, MAP_SELECT_LEFT_ARROW_POSITION, Tower, TOWER_HOTKEYS, UPGRADE_HOTKEYS
from interaction import WindowManager, InputController
from money_reader import MoneyReader
from system_flags import vprint, PIXELS_PER_BLOONS_UNIT
from vision import identify_screen, get_current_tab


@dataclass
class PlacedTower:
    tower: Tower
    position: tuple[float, float]
    upgrades: dict = field(default_factory=lambda: {"top": 0, "middle": 0, "bottom": 0})
    radius_px: int = 0
    id: int = field(default_factory=lambda: int(time.time() * 1000))


class BloonsBrain:
    def __init__(self, window_title: str = "BloonsTD6"):
        # Track data
        self.selected_track: Track | None = None
        self.track_mask = None
        self.land_mask = None
        self.water_mask = None
        self.flow_points = None

        # Game data
        self.difficulty: BloonsDifficulty | None = None
        self.gamemode: BloonsGamemode | None = None
        self.placed_towers: list[PlacedTower] = []
        self.occupied_mask = None
        self._estimated_money: int = 0
        self._last_money_estimate_time: float | None = None

        # Window controller
        self.window_manager = WindowManager(window_title)
        if not self.window_manager.wait_for_window():
            raise RuntimeError(f"Window '{window_title}' not found.")
        self.controller: InputController = self.window_manager.get_relative_controller()

        # Money reader thread
        self.money_reader = MoneyReader(self.window_manager, interval=3)

        # Tower data
        with open("data/combined_towers.json", "r", encoding="utf-8") as f:
            self.tower_data = json.load(f)
        with open("data/merged_upgrades.json", "r", encoding="utf-8") as f:
            self.upgrade_data = json.load(f)

    @property
    def money(self) -> int | None:
        """Return the most recent know money value (either from reader or estimate)"""
        ocr_money, ocr_time = self.money_reader.get_money()
        if self._last_money_estimate_time is None:
            self._estimated_money = ocr_money
            return ocr_money
        if ocr_time is None:
            return self._estimated_money
        return ocr_money if ocr_time >= self._last_money_estimate_time else self._estimated_money

    def update_money_estimate(self, change: int):
        if self._estimated_money is None:
            self._estimated_money = 0
        self._estimated_money = max(self._estimated_money + change, 0)
        self._last_money_estimate_time = time.time()

    def get_tower_info(self, tower: Tower) -> dict:
        return self.tower_data[tower.value]

    def get_tower_range_px(self, tower: Tower) -> int:
        return int(self.get_tower_info(tower)["base_range"] * PIXELS_PER_BLOONS_UNIT)

    def get_tower_cost(self, tower: Tower) -> int:
        return self.get_tower_info(tower)["base_costs"][self.difficulty.value]

    def get_tower_coverage(self, tower: PlacedTower) -> dict:
        """Return a dictionary of tower coverage."""
        tower_info = self.get_tower_info(tower.tower)
        coverage = {"camo": tower_info["base_sees_camo"], "lead": tower_info["base_pops_lead"]}
        for path in tower.upgrades:
            for tier in range(1, tower.upgrades[path] + 1):
                upgrade = self._get_upgrade(tower.tower, path, tier)
                if upgrade:
                    if upgrade["grants_camo"]:
                        coverage["camo"] = True
                    if upgrade["grants_lead"]:
                        coverage["lead"] = True
        return coverage

    def get_tower_radius_px(self, tower: Tower) -> int:
        tower_info = self.get_tower_info(tower)
        shape = tower_info["footprint_shape"]
        if shape == "circular":
            return int(tower_info["footprint_radius"] * PIXELS_PER_BLOONS_UNIT)
        elif shape == "rectangular":
            # Approximate rectangle as a circle with radius = half the diagonal
            w = tower_info.get("footprint_width", 10)
            h = tower_info.get("footprint_height", 10)
            radius = (w ** 2 + h ** 2) ** 0.5 / 2
            return int(radius * PIXELS_PER_BLOONS_UNIT)
        else:
            # Fallback
            return int(10 * PIXELS_PER_BLOONS_UNIT)

    def get_global_coverage(self) -> dict:
        has_camo = False
        has_lead = False
        for t in self.placed_towers:
            coverage = self.get_tower_coverage(t)
            has_camo |= coverage["camo"]
            has_lead |= coverage["lead"]
        return {"camo": has_camo, "lead": has_lead}

    def select_track(self, track: Track):
        """Load track data for the specified track folder"""
        # Standard paths
        track_folder_path = f"data/tracks/{track.value.lower().replace(' ', '_')}"
        track_mask_path = f"{track_folder_path}/track_mask.png"
        land_mask_path = f"{track_folder_path}/land_placement_mask.png"
        water_mask_path = f"{track_folder_path}/water_placement_mask.png"
        track_json_path = f"{track_folder_path}/path_points.json"

        # Track mask
        self.track_mask = cv2.imread(track_mask_path)
        if self.track_mask is None:
            raise RuntimeError(f"Could not load track mask: '{track_mask_path}'")

        # Placement masks
        self.land_mask = cv2.imread(land_mask_path)
        if self.land_mask is None:
            raise RuntimeError(f"Could not load land placement mask: '{land_mask_path}'")

        self.water_mask = cv2.imread(water_mask_path)
        if self.water_mask is None:
            raise RuntimeError(f"Could not load water placement mask: '{water_mask_path}'")

        # Occupied spaces mask
        self.occupied_mask = np.zeros_like(self.land_mask[:, :, 0], dtype=np.uint8)

        # Flow points
        with open(track_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.flow_points = data.get("flow_points", [])
        if not self.flow_points:
            raise RuntimeError(f"No flow points found in '{track_json_path}'.")

        self.selected_track = track

    def set_gamemode(self, gamemode: BloonsGamemode):
        """Set gamemode and difficulty."""
        self.gamemode = gamemode

        # Derive difficulty automatically from GAMEMODE_SELECT_POSITIONS
        for difficulty, gamemode_dict in GAMEMODE_SELECT_POSITIONS.items():
            if gamemode in gamemode_dict:
                self.difficulty = difficulty
                return

        raise ValueError(f"Could not derive difficulty for gamemode: {gamemode}")

    def wait_for_screen(self, target: BloonsScreen, timeout: float = 10.0, interval: float = 0.5) -> bool:
        """
        Wait until the game reaches the given screen, or timeout.
        Returns True if successful, False if timeout reached.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_screen = identify_screen(self.window_manager.capture_window(force_focus=True))
            if current_screen == target:
                return True
            time.sleep(interval)
        return False

    @staticmethod
    def _find_path(start: BloonsScreen, goal: BloonsScreen):
        """Find the shortest path between two screens (BFS)"""
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
        """Handle transitions that need special logic"""
        # Transition from map select to in-game
        if src == BloonsScreen.MAP_SELECT and dst in (BloonsScreen.IN_GAME, BloonsScreen.SANDBOX_START_POPUP):
            if self.difficulty is None:
                raise RuntimeError("Difficulty not set.")

            current_tab_idx = get_current_tab(self.window_manager.capture_window(force_focus=True)) - 1
            if current_tab_idx is None:
                raise RuntimeError("Current tab index not provided.")

            # Get thumbnail position
            target_page_idx, thumbnail_index = TRACK_THUMBNAIL_LOCATIONS[self.selected_track]

            # Move to the correct map select tab
            for _ in range(abs(target_page_idx - current_tab_idx)):
                if target_page_idx > current_tab_idx:
                    self.controller.click(*MAP_SELECT_RIGHT_ARROW_POSITION, duration=0.05)
                else:
                    self.controller.click(*MAP_SELECT_LEFT_ARROW_POSITION, duration=0.05)

            # Select the correct map thumbnail
            if None in (target_page_idx, thumbnail_index):
                raise RuntimeError(f"No thumbnail location found for map: {self.selected_track}")
            if thumbnail_index >= len(MAP_SELECT_THUMBNAIL_POSITIONS):
                raise RuntimeError(f"Map index {thumbnail_index} out of range.")
            map_pos = MAP_SELECT_THUMBNAIL_POSITIONS[thumbnail_index]
            vprint(f"Clicking map at position {thumbnail_index + 1} ({map_pos})")
            self.controller.click(*map_pos)
            time.sleep(0.2)

            # Select difficulty
            diff_pos = DIFFICULTY_SELECT_POSITIONS[self.difficulty]
            vprint(f"Selecting difficulty {self.difficulty.name} at {diff_pos}")
            self.controller.click(*diff_pos)
            time.sleep(0.2)

            # Select gamemode
            gm_pos = GAMEMODE_SELECT_POSITIONS[self.difficulty].get(self.gamemode)
            if gm_pos is None:
                raise RuntimeError(f"Gamemode {self.gamemode} not valid for {self.difficulty.name}.")
            vprint(f"Selecting gamemode {self.gamemode} at {gm_pos}")
            self.controller.click(*gm_pos)

            return True
        raise RuntimeError(f"No special handler for {src} → {dst}")

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

    def _get_upgrade(self, tower: Tower, path: str, tier: int):
        upgrades = self.upgrade_data[tower]
        path_num = {"top": 1, "middle": 2, "bottom": 3}[path]
        for upgrade in upgrades:
            if upgrade["path"] == path_num and upgrade["tier"] == tier:
                return upgrade
        raise ValueError(f"Upgrade not found for {tower.value} at tier {tier} on path {path}.")

    def get_next_upgrade(self, tower: PlacedTower, path: str):
        """Get the next upgrade for a tower in the provided path"""
        next_tier = tower.upgrades[path] + 1
        return self._get_upgrade(tower.tower, path, next_tier)

    def upgrade_tower(self, tower_obj: PlacedTower, path: str):
        """Upgrade a tower to the next tier in the provided path"""
        if path not in tower_obj.upgrades:
            raise ValueError(f"Invalid path '{path}', must be 'top', 'middle', or 'bottom'.")

        upgrade = self.get_next_upgrade(tower_obj, path)
        cost = upgrade["cost"][self.difficulty.value]
        if self.money < cost:
            raise RuntimeError(
                f"Not enough money to upgrade {tower_obj.tower.value} ({path} → {tower_obj.upgrades[path]})")

        self.controller.click(*tower_obj.position)
        self.controller.press_key(UPGRADE_HOTKEYS[path])
        time.sleep(0.1)
        self.controller.click(*tower_obj.position)

        vprint(
            f"Upgraded {tower_obj.tower.value} with {upgrade['name']} ({path} → {tower_obj.upgrades[path]}) for ${cost}/{self.money}"
        )

        self.update_money_estimate(-cost)

        # Increment internal tracking
        tower_obj.upgrades[path] += 1

    def can_place_tower_on_map(self, tower: Tower, sample_step: int = 20) -> bool:
        """Check if the tower can be placed anywhere"""
        tower_info = self.get_tower_info(tower)
        placement_type = tower_info["placement_type"]

        if placement_type == "land":
            mask = self.land_mask
        elif placement_type == "water":
            mask = self.water_mask
        elif placement_type == "any":
            mask = cv2.bitwise_or(self.land_mask, self.water_mask)
        else:
            return False

        if mask is None:
            return False

        tower_radius = self.get_tower_radius_px(tower)
        h, w = mask.shape[:2]

        for y in range(0, h, sample_step):
            for x in range(0, w, sample_step):
                if mask[y, x, 0] < 128:
                    continue
                y0 = max(y - tower_radius, 0)
                y1 = min(y + tower_radius, h)
                x0 = max(x - tower_radius, 0)
                x1 = min(x + tower_radius, w)

                # Ensure it doesn't overlap the track
                if np.any(self.track_mask[y0:y1, x0:x1, 0] > 128):
                    continue

                # Found at least one valid spot
                return True

        return False

    def calculate_tower_dps(self, tower_obj: PlacedTower) -> float:
        """
        Calculate an estimated DPS for the given placed tower, including upgrades.
        Only considers basic damage, pierce, and cooldown. Effects like abilities,
        special attacks, or area-of-effect multipliers are not included here.
        """
        info = self.get_tower_info(tower_obj.tower)

        # Start with base stats
        cooldown = info.get("cooldown", 1.0)
        damage = info.get("damage", 0)
        pierce = info.get("pierce", 1)
        projectiles = info.get("projectiles", 1)

        # Apply upgrades
        for path_name, tier in tower_obj.upgrades.items():
            for t in range(1, tier + 1):
                try:
                    upgrade = self._get_upgrade(tower_obj.tower, path_name, t)
                except ValueError:
                    continue
                damage = upgrade.get("Damage", damage)
                cooldown = upgrade.get("Cooldown", cooldown)
                pierce = upgrade.get("Pierce", pierce)
                projectiles = upgrade.get("Projectiles", projectiles)

        if cooldown <= 0:
            return 0.0  # avoid division by zero
        dps = (damage * pierce * projectiles) / cooldown
        return dps

    def calculate_global_dps(self) -> dict:
        """
        Calculate total DPS across all placed towers.
        Also return total DPS for towers that can pop leads and detect camos.
        """
        total_dps = 0.0
        total_lead_dps = 0.0
        total_camo_dps = 0.0

        for tower_obj in self.placed_towers:
            dps = self.calculate_tower_dps(tower_obj)
            total_dps += dps

            coverage = self.get_tower_coverage(tower_obj)
            if coverage.get("lead"):
                total_lead_dps += dps
            if coverage.get("camo"):
                total_camo_dps += dps

        return {
            "total_dps": total_dps,
            "lead_dps": total_lead_dps,
            "camo_dps": total_camo_dps,
        }

    def evaluate_tower_dps_efficiency(self, tower: Tower) -> float:
        """Estimate DPS per dollar for a tower with no upgrades."""
        try:
            dummy = PlacedTower(tower=tower, position=(0, 0))
            dps = self.calculate_tower_dps(dummy)
            cost = self.get_tower_cost(tower)
            return dps / cost if cost > 0 else 0
        except Exception:
            return 0.0

    def evaluate_upgrade_dps_efficiency(self, tower_obj: PlacedTower, path: str) -> float:
        """Estimate DPS gain per dollar for the next upgrade."""
        try:
            current_dps = self.calculate_tower_dps(tower_obj)
            next_tier = tower_obj.upgrades[path] + 1
            upgrade = self._get_upgrade(tower_obj.tower, path, next_tier)
            cost = upgrade["cost"][self.difficulty.value]
            if cost <= 0:
                return 0.0

            # Simulate DPS after upgrade
            simulated = PlacedTower(
                tower=tower_obj.tower,
                position=tower_obj.position,
                upgrades={**tower_obj.upgrades, path: next_tier},
            )
            new_dps = self.calculate_tower_dps(simulated)
            gain = new_dps - current_dps
            return gain / cost if gain > 0 else 0.0
        except Exception:
            return 0.0

    def find_best_placement(self, tower: Tower, sample_step: int = 15) -> tuple[float, float]:
        """
        Find a good placement position for the tower:
        - Valid terrain (land/water)
        - Doesn't overlap the track (tower radius clearance)
        - Maximizes coverage of flow points
        """

        if self.selected_track is None or self.flow_points is None:
            raise RuntimeError("No track selected or flow points not loaded.")

        tower_info = self.get_tower_info(tower)
        placement_type = tower_info["placement_type"]
        base_range = self.get_tower_range_px(tower)
        tower_radius = self.get_tower_radius_px(tower)

        # Placement mask
        if placement_type == "land":
            mask = self.land_mask
        elif placement_type == "water":
            mask = self.water_mask
        elif placement_type == "any":
            mask = self.land_mask | self.water_mask
        else:
            raise ValueError(f"Unknown placement type: {placement_type}")

        if mask is None:
            raise RuntimeError(f"No mask loaded for {placement_type} placement.")

        # Track mask should be loaded
        if self.track_mask is None:
            raise RuntimeError("Track mask not loaded.")

        flow_pts = np.array(self.flow_points)
        if flow_pts.shape[1] != 2:
            raise ValueError("Flow points must be (x, y) pairs.")

        h, w = mask.shape[:2]
        best_score = -1
        best_pos = None

        # Scan the whole screen for the best placement
        range_sq = base_range ** 2
        tower_r = int(np.ceil(tower_radius))
        for y in range(0, h, sample_step):
            for x in range(0, w, sample_step):
                # Check terrain
                if mask[y, x, 0] < 128:
                    continue

                # Skip placements too close to the track
                y0 = max(y - tower_r, 0)
                y1 = min(y + tower_r, h)
                x0 = max(x - tower_r, 0)
                x1 = min(x + tower_r, w)
                sub_track = self.track_mask[y0:y1, x0:x1, 0]

                if np.any(sub_track > 128):  # track present inside radius
                    continue

                # Skip placements too close to other towers
                if np.any(self.occupied_mask[y0:y1, x0:x1] > 0):
                    continue

                # Score based on nearby flow points
                dist2 = (flow_pts[:, 0] - x) ** 2 + (flow_pts[:, 1] - y) ** 2
                score = np.sum(dist2 < range_sq)

                if score > best_score:
                    best_score = score
                    best_pos = (x, y)

        if best_pos is None:
            raise RuntimeError(f"No valid placement found for {tower.value} on {self.selected_track}.")

        norm_x = best_pos[0] / w
        norm_y = best_pos[1] / h
        vprint(f"Best {tower.value} placement: ({norm_x:.3f}, {norm_y:.3f}) — covers {best_score} flow points")

        return norm_x, norm_y

    ############### STRATEGY/HEURISTICS ###############

    def evaluate_tower_future_value(self, tower: Tower, discount: float = 0.7) -> float:
        """
        Estimate a tower's overall upgrade potential.
        Weighted sum of DPS/cost improvements for all upgrades,
        discounted by how deep they are in the path.
        """
        try:
            upgrades = self.upgrade_data[tower]
        except KeyError:
            return 0.0

        total_value = 0.0
        for upgrade in upgrades:
            # Ignore crosspath-locked tiers above 2 unless they're pure
            if upgrade["tier"] > 5 or upgrade["cost"][self.difficulty.value] <= 0:
                continue

            cost = upgrade["cost"][self.difficulty.value]
            dmg = upgrade.get("Damage", 0)
            pierce = upgrade.get("Pierce", 1)
            proj = upgrade.get("Projectiles", 1)
            cd = upgrade.get("Cooldown", 1.0)

            # Simple DPS estimate
            dps = (dmg * pierce * proj) / cd if cd > 0 else 0
            value = (dps / cost) * (discount ** (upgrade["tier"] - 1))

            total_value += value

        return total_value

    def evaluate_tower_placement(self, tower, pos):
        # Reward towers that cover more flow points
        range_px = self.get_tower_range_px(tower)
        h, w = self.land_mask.shape[:2]
        x, y = int(pos[0] * w), int(pos[1] * h)
        flow_pts = np.array(self.flow_points)
        dist2 = (flow_pts[:, 0] - x) ** 2 + (flow_pts[:, 1] - y) ** 2
        coverage_score = np.sum(dist2 < range_px ** 2)

        # Penalize adding too many of the same tower
        same_type_count = sum(1 for t in self.placed_towers if t.tower == tower)
        penalty = same_type_count * 0.3  # tune this weight

        # Reward diversity
        unique_towers = len({t.tower for t in self.placed_towers})
        diversity_bonus = 1 + 0.05 * unique_towers

        score = coverage_score * (1 - penalty) * diversity_bonus

        return score

    def evaluate_upgrade(self, tower_obj, path):
        next_tier = tower_obj.upgrades[path] + 1
        upgrade = self.get_next_upgrade(tower_obj, path)
        score = 1.0

        # Reward higher tier upgrades
        score += next_tier * 0.5

        # Slightly reward upgrades that grant coverage (regardless of global coverage)
        if upgrade.get("grants_camo") or upgrade.get("grants_lead"):
            score *= 1.2

        # Reward upgrades that grant missing coverage
        global_coverage = self.get_global_coverage()
        if not global_coverage["camo"] and upgrade.get("grants_camo"):
            score *= 2.0
        if not global_coverage["lead"] and upgrade.get("grants_lead"):
            score *= 2.0

        # Special coverage for camo leads
        tower_coverage = self.get_tower_coverage(tower_obj)
        if tower_coverage["camo"] and upgrade.get("grants_lead"):
            score *= 2.0
        elif tower_coverage["lead"] and upgrade.get("grants_camo"):
            score *= 2.0

        return score

    def find_best_action(self, tower_list: list[Tower]):
        actions = []
        global_cov = self.get_global_coverage()
        tower_count = len(self.placed_towers)

        # Punish tower placements more as more towers are placed
        placement_bias = max(0.05, 1.0 - tower_count * 0.1)

        # Tower placements
        for tower in tower_list:
            cost = self.get_tower_cost(tower)
            if self.money < cost:
                continue

            # Skip towers that cannot be placed anywhere on this map
            if not self.can_place_tower_on_map(tower):
                vprint(f"Skipping {tower.value} — no valid placement area.")
                continue

            pos = self.find_best_placement(tower)
            dps_eff = self.evaluate_tower_dps_efficiency(tower)
            future_value = self.evaluate_tower_future_value(tower)
            score = self.evaluate_tower_placement(tower, pos) * placement_bias * (
                    1 + (dps_eff + 0.2 * future_value) * 100)

            # Favor towers that add missing coverage
            tower_info = self.get_tower_info(tower)
            if not global_cov["camo"] and tower_info["base_sees_camo"]:
                score *= 1.5
            if not global_cov["lead"] and tower_info["base_pops_lead"]:
                score *= 1.5

            actions.append(("place", tower, pos, score))

        # Tower upgrades
        for placed in self.placed_towers:
            for path in ("top", "middle", "bottom"):
                current_tier = placed.upgrades[path]

                # Skip if this path is already maxed
                if current_tier >= 5:
                    continue
                other_paths = [p for p in ("top", "middle", "bottom") if p != path]
                other_tiers = [placed.upgrades[p] for p in other_paths]

                # If both other paths are already upgraded, skip this path
                if all(t > 0 for t in other_tiers):
                    continue

                # If another tier is already >2, this path can't go higher than 2
                if max(other_tiers) >= 3 and current_tier == 2:
                    continue

                try:
                    upgrade = self.get_next_upgrade(placed, path)
                    if upgrade:
                        cost = upgrade["cost"][self.difficulty.value]
                        if self.money < cost:
                            continue
                        dps_eff = self.evaluate_upgrade_dps_efficiency(placed, path)
                        score = self.evaluate_upgrade(placed, path) * (1 + dps_eff * 100)

                        actions.append(("upgrade", placed, path, score))
                except Exception:
                    continue

        if not actions:
            return None  # nothing to do

        # Pick the best-scoring action
        best_action = max(actions, key=lambda a: a[3])
        return best_action


def main():
    brain = BloonsBrain()

    # Select game settings
    brain.select_track(Track.ALPINE_RUN)
    brain.set_gamemode(BloonsGamemode.IMPOPPABLE)

    banned_towers = [Tower.GLUE_GUNNER, Tower.MONKEY_VILLAGE]
    tower_list = [tower for tower in Tower if tower not in banned_towers]

    if brain.gamemode in (BloonsGamemode.EASY_SANDBOX, BloonsGamemode.MEDIUM_SANDBOX, BloonsGamemode.HARD_SANDBOX):
        target_screen = BloonsScreen.SANDBOX_MONKEY_SCREEN
    else:
        target_screen = BloonsScreen.IN_GAME

    # Get into the game
    brain.navigate_to(target_screen)

    # Start the money reader
    brain.money_reader.start()

    while True:
        current_screen = identify_screen(brain.window_manager.capture_window(force_focus=True))
        if current_screen != BloonsScreen.IN_GAME:
            print(f"Detected screen change ({current_screen}), waiting 5 seconds to confirm...")
            time.sleep(5)

            recheck_screen = identify_screen(brain.window_manager.capture_window(force_focus=False))
            if recheck_screen != BloonsScreen.IN_GAME:
                print(f"Still not in-game after wait ({recheck_screen}), exiting loop.")
                break
            else:
                print("Screen recovered — resuming automation.")

        # try:
        action = brain.find_best_action(tower_list)
        if not action:
            time.sleep(1)
            continue

        kind = action[0]
        if kind == "place":
            _, tower, pos, _ = action
            brain.place_tower(tower, pos)
        elif kind == "upgrade":
            _, tower_obj, path, _ = action
            brain.upgrade_tower(tower_obj, path)

        # Collect any bananas from the map
        for farm in [t for t in brain.placed_towers if t.tower == Tower.BANANA_FARM]:
            brain.controller.move(*farm.position)

        # except Exception as e:
        #     print(f"Action failed: {e}")

        time.sleep(0.2)


if __name__ == "__main__":
    main()
