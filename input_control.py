import enum
import time

import pyautogui as pgui


class MouseButtons(enum.StrEnum):
    LEFT_MOUSE = "left"
    RIGHT_MOUSE = "right"
    MIDDLE_MOUSE = "middle"


class InputController:
    def __init__(self, pause: float = 0.05):
        pgui.PAUSE = pause

    @property
    def screen_size(self):
        return pgui.size()

    @staticmethod
    def move(x: float, y: float, duration: float = 0.2, tween=pgui.easeOutQuad):
        """Move mouse to (x, y) without clicking."""
        pgui.moveTo(x, y, duration, tween=tween)

    @staticmethod
    def click(
            x: float,
            y: float,
            button: MouseButtons = MouseButtons.LEFT_MOUSE,
            duration: float = 0.2,
            tween=pgui.easeOutQuad
    ):
        """Click at position x, y (optional duration/tween)"""
        pgui.moveTo(x, y, duration, tween=tween)
        pgui.click(button=button)

    @staticmethod
    def drag(
            start_pos: tuple[float, float],
            end_pos: tuple[float, float],
            key: MouseButtons | str = MouseButtons.LEFT_MOUSE,
            duration: float = 0.2,
            tween=pgui.easeOutQuad
    ):
        """Drag from start_pos to end_pos using either a click or a pressed key (optional duration/tween)"""
        pgui.moveTo(*start_pos, duration=duration / 2, tween=tween)

        if isinstance(key, MouseButtons):
            pgui.dragTo(*end_pos, duration=duration, tween=tween, button=key)
        else:
            pgui.keyDown(key)
            pgui.moveTo(*end_pos, duration=duration, tween=tween)
            pgui.keyUp(key)


def main():
    controller = InputController()
    w, h = controller.screen_size

    time.sleep(1)
    controller.click(w / 2, h / 2)


if __name__ == '__main__':
    main()
