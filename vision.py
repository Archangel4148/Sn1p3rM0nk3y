import cv2
import easyocr
import numpy as np
from PIL import ImageOps, Image

from data.enums import BloonsScreen, PAGE_IDENTIFIER_POINTS, MAP_SELECT_PAGE_POINTS, SELECTED_MAP_SELECT_TAB_COLOR
from system_flags import vprint, VERBOSE, SUPPRESS_SCREEN_MATCHING_OUTPUT


def color_close(a, b, tol=5):
    return all(abs(a[i] - b[i]) <= tol for i in range(3))


def identify_screen(capture) -> BloonsScreen | None:
    """Identify the screen using sets of pixel identifiers.
    Each screen can have multiple valid match sets — if any set matches fully, the screen is identified.
    """

    for screen, match_sets in PAGE_IDENTIFIER_POINTS.items():
        # Each screen can have several possible match configurations
        for match_set in match_sets:
            all_points_match = True

            for (w_frac, h_frac), expected_color in match_set:
                px = int(capture.width * w_frac)
                py = int(capture.height * h_frac)
                actual_color = capture.getpixel((px, py))

                if not color_close(actual_color, expected_color):
                    all_points_match = False
                    if not VERBOSE:
                        break  # Skip early if mismatch and not debugging
                    if not SUPPRESS_SCREEN_MATCHING_OUTPUT:
                        vprint(f"{screen.name} point mismatch {actual_color} != {expected_color}")

                else:
                    if not SUPPRESS_SCREEN_MATCHING_OUTPUT:
                        vprint(f"{screen.name} point OK {actual_color} ≈ {expected_color}")

            # If all points in this match set matched, the screen is identified
            if all_points_match:
                if not SUPPRESS_SCREEN_MATCHING_OUTPUT:
                    vprint(f"Matched screen: {screen.name}")
                return screen
    if not SUPPRESS_SCREEN_MATCHING_OUTPUT:
        vprint("Could not identify current screen.")
    return None


def get_current_tab(capture):
    # Check each tab dot
    for i, (w_fraction, h_fraction) in enumerate(MAP_SELECT_PAGE_POINTS):
        point_color = capture.getpixel(
            (int(capture.width * w_fraction), int(capture.height * h_fraction)))
        # Find the selected map select tab
        if color_close(point_color, SELECTED_MAP_SELECT_TAB_COLOR):
            vprint(f"Found tab: {i + 1}")
            return i + 1

    vprint("Could not identify selected map tab.")
    return None


def ocr_number_from_image(pil_img: Image.Image) -> int | None:
    # Convert to grayscale
    gray = ImageOps.grayscale(pil_img)
    img_array = np.array(gray)
    _, img_bin = cv2.threshold(img_array, 180, 255, cv2.THRESH_BINARY)

    # OCR
    reader = easyocr.Reader(["en"], gpu=True)
    results = reader.readtext(img_bin)

    if not results:
        return None

    # Take the first detected text and filter digits
    text = ''.join(filter(str.isdigit, results[0][1]))

    return int(text) if text else None

import torch
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No GPU detected")