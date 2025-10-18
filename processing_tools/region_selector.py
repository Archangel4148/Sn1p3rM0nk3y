import time
import cv2
import numpy as np
from interaction import WindowManager

def pick_rectangle(window_title: str = "BloonsTD6"):
    wm = WindowManager(window_title)
    if not wm.wait_for_window():
        raise RuntimeError(f"Window '{window_title}' not found.")

    # Capture the current window
    image = wm.capture_window(force_focus=True)
    frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    h, w, _ = frame.shape

    rect_start = None
    rect_end = None
    drawing = False
    output_frame = frame.copy()

    def on_mouse(event, x, y, flags, param):
        nonlocal rect_start, rect_end, drawing, output_frame
        if event == cv2.EVENT_LBUTTONDOWN:
            rect_start = (x, y)
            drawing = True
        elif event == cv2.EVENT_MOUSEMOVE and drawing:
            output_frame = frame.copy()
            cv2.rectangle(output_frame, rect_start, (x, y), (0, 255, 0), 2)
        elif event == cv2.EVENT_LBUTTONUP:
            rect_end = (x, y)
            drawing = False
            output_frame = frame.copy()
            cv2.rectangle(output_frame, rect_start, rect_end, (0, 0, 255), 2)
            print_rectangle_info(rect_start, rect_end, w, h)

    def print_rectangle_info(start, end, width, height):
        x1, y1 = start
        x2, y2 = end
        abs_coords = (x1, y1, x2, y2)
        rel_coords = (x1 / width, y1 / height, x2 / width, y2 / height)
        print("Rectangle drawn:")
        print(f"  Absolute coords: {abs_coords}")
        print(f"  Relative coords: ({rel_coords[0]:.3f}, {rel_coords[1]:.3f}, {rel_coords[2]:.3f}, {rel_coords[3]:.3f})")

    cv2.namedWindow("Bloons Screenshot")
    cv2.setMouseCallback("Bloons Screenshot", on_mouse)

    print("Draw a rectangle by clicking and dragging the mouse. Press any key to exit.")

    while True:
        cv2.imshow("Bloons Screenshot", output_frame)
        key = cv2.waitKey(1)
        if key != -1:
            break

    cv2.destroyAllWindows()
    if rect_start and rect_end:
        return (rect_start, rect_end)
    return None

def main():
    result = pick_rectangle("BloonsTD6")
    if result:
        print(f"Final rectangle: {result}")
    else:
        print("No rectangle was drawn.")

if __name__ == "__main__":
    main()
