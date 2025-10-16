import cv2
import numpy as np
import os

# --- Config ---
track_mask_path = "../data/tracks/monkey_meadow/monkey_meadow_track_mask.png"
wall_mask_path = "../data/tracks/monkey_meadow/monkey_meadow_wall_mask.png"
water_mask_path = "../data/tracks/monkey_meadow/monkey_meadow_water_mask.png"

output_land_path = "../data/tracks/monkey_meadow/monkey_meadow_land_placement_mask.png"
output_water_path = "../data/tracks/monkey_meadow/monkey_meadow_water_placement_mask.png"

# --- Load masks as grayscale ---
track_mask = cv2.imread(track_mask_path, cv2.IMREAD_GRAYSCALE)
wall_mask = cv2.imread(wall_mask_path, cv2.IMREAD_GRAYSCALE)
water_mask = cv2.imread(water_mask_path, cv2.IMREAD_GRAYSCALE)

if track_mask is None or wall_mask is None or water_mask is None:
    raise FileNotFoundError("One or more masks could not be loaded!")

# --- Normalize to binary (255 or 0) ---
track_mask = cv2.threshold(track_mask, 127, 255, cv2.THRESH_BINARY)[1]
wall_mask = cv2.threshold(wall_mask, 127, 255, cv2.THRESH_BINARY)[1]
water_mask = cv2.threshold(water_mask, 127, 255, cv2.THRESH_BINARY)[1]

# --- Compute valid placement areas ---
# Valid land = not wall, not track, not water
valid_land_mask = np.ones_like(track_mask, dtype=np.uint8) * 255
valid_land_mask[(track_mask == 255) | (wall_mask == 255) | (water_mask == 255)] = 0

# Valid water = water but not wall or track
valid_water_mask = np.copy(water_mask)
valid_water_mask[(wall_mask == 255) | (track_mask == 255)] = 0

# --- Save masks ---
os.makedirs(os.path.dirname(output_land_path), exist_ok=True)
cv2.imwrite(output_land_path, valid_land_mask)
cv2.imwrite(output_water_path, valid_water_mask)
print(f"Saved valid land mask → {output_land_path}")
print(f"Saved valid water mask → {output_water_path}")

# --- Display results (scaled for convenience) ---
scale = min(1.0, 1000 / track_mask.shape[1], 700 / track_mask.shape[0])
show_land = cv2.resize(valid_land_mask, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
show_water = cv2.resize(valid_water_mask, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)

cv2.imshow("Valid Land Mask", show_land)
cv2.imshow("Valid Water Mask", show_water)
cv2.waitKey(0)
cv2.destroyAllWindows()
