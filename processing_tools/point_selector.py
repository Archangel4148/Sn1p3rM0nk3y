import cv2
import json
import numpy as np
from interaction import WindowManager


def pick_color_point(window_title: str = "BloonsTD6"):
    wm = WindowManager(window_title)
    if not wm.wait_for_window():
        raise RuntimeError(f"Window '{window_title}' not found.")

    # Capture the current Bloons window
    image = wm.capture_window(force_focus=True)
    frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    h, w, _ = frame.shape

    clicked_point = {"pos": None, "color": None}

    def on_click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            b, g, r = frame[y, x]
            clicked_point["pos"] = (x, y)
            clicked_point["color"] = (r, g, b)
            print(f"Clicked pixel:")
            print(f"  Absolute position: ({x}, {y})")
            print(f"  Relative factors: ({x / w:.3f}, {y / h:.3f})")
            print(f"  Color (RGB): {r}, {g}, {b}")

    cv2.namedWindow("Bloons Screenshot")
    cv2.setMouseCallback("Bloons Screenshot", on_click)

    print("Click anywhere on the image to get pixel data. Press any key to exit.")

    while True:
        cv2.imshow("Bloons Screenshot", frame)
        key = cv2.waitKey(1)
        if key != -1:
            break

    cv2.destroyAllWindows()
    return clicked_point


def main():
    result = pick_color_point("BloonsTD6")
    if result["pos"]:
        print("\nFinal selected point:")
        print(json.dumps(result, indent=2))
    else:
        print("No point was selected.")


if __name__ == "__main__":
    main()