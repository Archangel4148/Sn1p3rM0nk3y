import enum
import time

import pyautogui as pgui
import pygetwindow as gw


class MouseButtons(enum.StrEnum):
    LEFT_MOUSE = "left"
    RIGHT_MOUSE = "right"
    MIDDLE_MOUSE = "middle"


class InputController:
    def __init__(self, pause: float = 0.05, window_geometry: tuple | None = None, window_ref=None):
        pgui.PAUSE = pause
        self.window_geometry = window_geometry
        self.window_ref = window_ref

    def set_window_geometry(self, geometry: tuple | None):
        """Attach or update the window geometry (None = use full screen)."""
        self.window_geometry = geometry

    def _screen_coords(self, x: float, y: float) -> tuple[float, float]:
        """Get the absolute screen coordinates of a relative window position
        (either a pixel coordinate or a fraction of the window size)"""
        if not self.window_geometry:
            return x, y  # No window, just use absolute coords

        left, top, width, height = self.window_geometry

        # Handle either a pixel position or a fraction of the window width
        x = left + (x * width if 0 <= x <= 1 else x)
        y = top + (y * height if 0 <= y <= 1 else y)
        return x, y

    def _is_in_window_bounds(self, x: float, y: float) -> bool:
        if not self.window_geometry:
            return True
        left, top, width, height = self.window_geometry
        return left <= x <= left + width and top <= y <= top + height

    def _is_window_focused(self) -> bool:
        if not self.window_ref:
            return True  # Assume true if no window is specified
        try:
            return self.window_ref.isActive
        except Exception:
            return False

    def _validate_position(self, x: float, y: float) -> tuple[float, float] | None:
        """Ensure the window is focused and coords are within bounds."""
        if not self._is_window_focused():
            print("Action aborted: target window is not focused.")
            return None

        x, y = self._screen_coords(x, y)
        if not self._is_in_window_bounds(x, y):
            print(f"Action aborted: ({x:.0f}, {y:.0f}) outside window bounds.")
            return None

        return x, y

    @property
    def screen_size(self):
        return pgui.size()

    def move(self, x: float, y: float, duration: float = 0.2, tween=pgui.easeOutQuad):
        """Move mouse to (x, y) without clicking."""
        x, y = self._validate_position(x, y)
        pgui.moveTo(x, y, duration, tween=tween)

    def click(
            self,
            x: float,
            y: float,
            button: MouseButtons = MouseButtons.LEFT_MOUSE,
            duration: float = 0.2,
            tween=pgui.easeOutQuad
    ):
        """Click at position x, y (optional duration/tween)"""
        x, y = self._validate_position(x, y)
        pgui.moveTo(x, y, duration, tween=tween)
        pgui.click(button=button)

    @staticmethod
    def press_key(key: str, hold_time: float = 0.05):
        """Press and release a keyboard key."""
        pgui.keyDown(key)
        time.sleep(hold_time)
        pgui.keyUp(key)

    @staticmethod
    def scroll(amount: int):
        """Scroll the mouse wheel. Positive=up, negative=down."""
        pgui.scroll(amount)

    def drag(
            self,
            start_pos: tuple[float, float],
            end_pos: tuple[float, float],
            key: MouseButtons | str = MouseButtons.LEFT_MOUSE,
            duration: float = 0.2,
            tween=pgui.easeOutQuad
    ):
        """Drag from start_pos to end_pos using either a click or a pressed key (optional duration/tween)"""
        start_pos = self._validate_position(*start_pos)
        end_pos = self._validate_position(*end_pos)
        if not start_pos or not end_pos:
            print("Drag aborted: invalid window state or coordinates.")
            return
        pgui.moveTo(*start_pos, duration=duration / 2, tween=tween)

        if isinstance(key, MouseButtons):
            pgui.dragTo(*end_pos, duration=duration, tween=tween, button=key)
        else:
            pgui.keyDown(key)
            pgui.moveTo(*end_pos, duration=duration, tween=tween)
            pgui.keyUp(key)


class WindowManager:
    def __init__(self, window_title: str):
        self.window_title = window_title
        self.window = self.find_window_by_title(window_title)

    @staticmethod
    def find_window_by_title(title: str):
        """Return the window object if found, else None."""
        for window in gw.getWindowsWithTitle(title):
            print(f"Found window: {window.title}")
            return window
        return None

    def wait_for_window(self, timeout: float = 10.0, interval: float = 0.5):
        """Wait for the target window to appear, checking every <interval> seconds until <timeout>"""
        start = time.time()
        while time.time() - start < timeout:
            self.recapture_window()
            if self.window:
                print(f"Window '{self.window_title}' detected.")
                return True
            time.sleep(interval)
        print(f"Timeout waiting for window '{self.window_title}'.")
        return False

    def recapture_window(self):
        """Re-find the target window (in case it was closed)"""
        self.window = self.find_window_by_title(self.window_title)

    def get_relative_controller(self) -> InputController:
        """Return an InputController bound to this window's current geometry."""
        return InputController(window_geometry=self.get_window_geometry(), window_ref=self.window)

    def focus_window(self):
        """Bring the target window to the foreground if possible."""
        if not self.window:
            print("No window found to focus.")
            return False

        try:
            if self.window.isMinimized:
                print(f"{self.window.title} is minimized, restoring window.")
                self.window.restore()
                pgui.sleep(0.5)  # Give it time to un-minimize

            self.window.activate()
            time.sleep(0.1)
            print(f"{self.window.title} focused successfully.")
            return True
        except Exception as e:
            print(f"Failed to focus window: {e}")
            return False

    def get_window_geometry(self):
        """Return (left, top, width, height) of the target window."""
        if not self.window:
            print("No window found.")
            return None
        # Cannot find geometry of a minimized window (background windows still work though!)
        if self.window.isMinimized:
            print(f"{self.window.title} is minimized, cannot find geometry...")
            return None

        win = self.window
        width, height = win.width, win.height
        return win.left, win.top, width, height

    def capture_window(self, filename: str | None = None):
        """Capture a screenshot of the window region and return it as a PIL image (optionally save it)"""
        geometry = self.get_window_geometry()
        if not geometry:
            print("Cannot capture screenshot — window not visible.")
            return None

        left, top, width, height = geometry
        screenshot = pgui.screenshot(region=(left, top, width, height))

        if filename:
            screenshot.save(filename)
            print(f"Saved screenshot to {filename}")

        return screenshot


def main():
    window_manager = WindowManager("BloonsTD6")
    time.sleep(1)
    window_manager.focus_window()
    window_manager.capture_window("test.png")
    controller = window_manager.get_relative_controller()
    controller.click(0.5, 0.9)


if __name__ == '__main__':
    main()
