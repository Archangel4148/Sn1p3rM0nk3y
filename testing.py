import json
import time

import cv2
import pyautogui as pgui

from interaction import WindowManager, InputController


def follow_track(json_path: str, window_title: str = "BloonsTD6", move_time: float = 0.15, delay: float = 0.1):
    """Move the mouse cursor through all flow points defined in the track JSON file."""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {json_path}")
        return

    flow_points = data.get("flow_points")
    if not flow_points:
        print("❌ No 'flow_points' found in JSON.")
        return

    print(f"Loaded {len(flow_points)} flow points from {json_path}")

    window_manager = WindowManager(window_title)
    if not window_manager.wait_for_window():
        print(f"❌ Could not find window titled '{window_title}'")
        return

    window_manager.focus_window()
    controller: InputController = window_manager.get_relative_controller()

    print("🚀 Starting track follow test... (press Ctrl+C to stop)\n")

    try:
        for i, (x, y) in enumerate(flow_points):
            controller.move(x, y, duration=move_time)
            print(f"[{i + 1}/{len(flow_points)}] → ({x:.1f}, {y:.1f})")
            time.sleep(delay)
    except KeyboardInterrupt:
        print("\n🟡 Interrupted by user.")
    except Exception as e:
        print(f"❌ Error during movement: {e}")

    print("✅ Track test complete.")


def test_valid_land_hover(valid_land_mask_path: str, window_title: str = "BloonsTD6"):
    """
    Continuously reports whether the mouse is hovering over a valid land placement pixel.
    Move mouse to top-left corner (0,0) to quit.
    """
    valid_land = cv2.imread(valid_land_mask_path, cv2.IMREAD_GRAYSCALE)
    if valid_land is None:
        print(f"❌ Could not load valid land mask from {valid_land_mask_path}")
        return

    window_manager = WindowManager(window_title)
    if not window_manager.wait_for_window():
        print(f"❌ Could not find window titled '{window_title}'")
        return

    geometry = window_manager.get_window_geometry()
    if geometry is None:
        print("❌ Could not get window geometry.")
        return

    left, top, width, height = geometry
    print(f"Monitoring mouse over window region ({width}x{height}). Move to (0,0) to quit.\n")

    try:
        while True:
            x, y = pgui.position()
            rel_x, rel_y = int(x - left), int(y - top)

            # Quit if moved to top-left corner (failsafe)
            if x <= 1 and y <= 1:
                print("\n🟡 Exiting test.")
                break

            if 0 <= rel_x < valid_land.shape[1] and 0 <= rel_y < valid_land.shape[0]:
                pixel_val = valid_land[rel_y, rel_x]
                valid = pixel_val > 127
                msg = f"({rel_x}, {rel_y}) → {'✅ VALID LAND' if valid else '❌ INVALID'}"
            else:
                print("Mouse outside window bounds, quitting...")
                break

            # Always print on a new line, avoids lost prints in normal mode
            print(msg)
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n🟡 Interrupted by user.")


def click_window_center(window_title: str = "BloonsTD6", repeat: int = 5, interval: float = 3.0):
    """Click in the center of the specified window every `interval` seconds."""
    window_manager = WindowManager(window_title)
    if not window_manager.wait_for_window():
        print(f"❌ Could not find window titled '{window_title}'")
        return

    window_manager.focus_window()
    controller: InputController = window_manager.get_relative_controller()

    print(f"Clicking center of '{window_title}' {repeat} times, every {interval} seconds...\n")
    for i in range(repeat):
        geom = window_manager.get_window_geometry()
        if not geom:
            print("❌ Could not get window geometry, aborting.")
            break

        print(f"[{i + 1}/{repeat}] Clicking center")
        controller.click(0.5, 0.5)
        time.sleep(interval)

    print("✅ Done clicking window center.")


def main():
    # Example track test
    track_json = "data/tracks/monkey_meadow/path_points.json"
    follow_track(track_json, move_time=0.01, delay=0.01)

    # Example hover test
    valid_land_mask_path = "data/tracks/monkey_meadow/land_placement_mask.png"
    test_valid_land_hover(valid_land_mask_path)

    # click_window_center(repeat=5, interval=3)


if __name__ == "__main__":
    main()
