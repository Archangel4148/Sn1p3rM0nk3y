import os

import cv2
import numpy as np
import pyautogui as pgui

# --- Config ---
track_folder_path = "../data/tracks/in_the_loop/"
screenshot_path = track_folder_path + "screenshot.png"
output_mask_path = track_folder_path + "wall_mask.png"
max_width, max_height = 1200, 800  # editor window size limit
color_tolerance = 10  # +/- tolerance in each BGR channel

# --- Ensure folder exists ---
os.makedirs(track_folder_path, exist_ok=True)

# Capture a screenshot
screenshot = pgui.screenshot()
screenshot.save(screenshot_path)

# --- Load screenshot ---
img = np.array(screenshot)

# --- Scale for editing ---
scale = min(1.0, max_width / img.shape[1], max_height / img.shape[0])
scaled_img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
mask_bgr = np.zeros_like(img)  # start with empty mask
scaled_mask = cv2.resize(mask_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)

# --- Painting setup ---
drawing = False
brush_size = 10
mode = "paint"
color_selected = False
track_color = None
overlay_mode = True  # True=overlay, False=mask-only

def generate_mask_from_color(color):
    """Generate mask based on selected BGR color with tolerance."""
    lower = np.clip(color - color_tolerance, 0, 255)
    upper = np.clip(color + color_tolerance, 0, 255)
    mask = cv2.inRange(img, lower, upper)
    mask = cv2.medianBlur(mask, 5)
    return cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

def mouse_callback(event, x, y, flags, param):
    global drawing, scaled_mask, mask_bgr, brush_size, mode, color_selected, track_color

    orig_x = int(x / scale)
    orig_y = int(y / scale)

    # Ctrl+Click: select track color
    if event == cv2.EVENT_LBUTTONDOWN and (flags & cv2.EVENT_FLAG_CTRLKEY):
        track_color = img[orig_y, orig_x]
        mask_bgr[:] = generate_mask_from_color(track_color)
        scaled_mask[:] = cv2.resize(mask_bgr, scaled_mask.shape[:2][::-1], interpolation=cv2.INTER_NEAREST)
        color_selected = True
        print(f"Selected track color: {track_color}")

    # Left-click (without Ctrl) → start drawing
    elif event == cv2.EVENT_LBUTTONDOWN:
        drawing = True

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False

    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        if mode == "paint":
            cv2.circle(mask_bgr, (orig_x, orig_y), brush_size, (0, 255, 0), -1)
        elif mode == "erase":
            cv2.circle(mask_bgr, (orig_x, orig_y), brush_size, (0, 0, 0), -1)
        scaled_mask[:] = cv2.resize(mask_bgr, scaled_mask.shape[:2][::-1], interpolation=cv2.INTER_NEAREST)

cv2.namedWindow("Mask Editor", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Mask Editor", scaled_img.shape[1], scaled_img.shape[0])
cv2.setMouseCallback("Mask Editor", mouse_callback)

print("Instructions:")
print("- Ctrl+Left-click: select track color (overwrite old mask)")
print("- Left-click drag: paint mask")
print("- 'e': toggle erase, '+/-': brush size")
print("- 't': toggle overlay / mask-only view")
print("- 's': save mask, 'q': quit without saving")

while True:
    if overlay_mode:
        display = cv2.addWeighted(scaled_img, 0.6, scaled_mask, 0.4, 0)
    else:
        display = scaled_mask.copy()
    cv2.imshow("Mask Editor", display)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):
        final_mask = cv2.cvtColor(mask_bgr, cv2.COLOR_BGR2GRAY)
        final_mask = cv2.threshold(final_mask, 1, 255, cv2.THRESH_BINARY)[1]
        cv2.imwrite(output_mask_path, final_mask)
        print(f"Saved mask to {output_mask_path}")
        break
    elif key == ord('e'):
        mode = "erase" if mode=="paint" else "paint"
        print("Mode:", mode)
    elif key == ord('t'):
        overlay_mode = not overlay_mode
        print("Overlay mode:", overlay_mode)
    elif key in (ord('+'), ord('=')):
        brush_size += 2
        print("Brush size:", brush_size)
    elif key == ord('-') and brush_size > 2:
        brush_size -= 2
        print("Brush size:", brush_size)

cv2.destroyAllWindows()
