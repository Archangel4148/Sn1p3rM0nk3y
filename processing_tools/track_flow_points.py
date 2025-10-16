import cv2
import numpy as np
import json

# --- Config ---
image_path = "../data/tracks/monkey_meadow/screenshot.png"
output_path = "../data/tracks/monkey_meadow/path_points.json"
max_width, max_height = 1200, 800
spacing = 20  # pixels between flow points

# --- Load image ---
img = cv2.imread(image_path)
if img is None:
    raise FileNotFoundError("Track image not found!")

# --- Scale for UI ---
scale = min(1.0, max_width / img.shape[1], max_height / img.shape[0])
img_scaled = cv2.resize(img, None, fx=scale, fy=scale)

points = []

def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        print(f"Added point {len(points)}: ({x}, {y})")

cv2.namedWindow("Define Path", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Define Path", img_scaled.shape[1], img_scaled.shape[0])
cv2.setMouseCallback("Define Path", mouse_callback)

print("Instructions:")
print("- Left-click to add a path corner")
print("- Press 'u' to undo last point")
print("- Press 's' to save and generate flow points")
print("- Press 'q' to quit")

def interpolate_path(points, spacing):
    """Return evenly spaced points along a polyline."""
    if len(points) < 2:
        return []

    # Calculate cumulative distance along path
    dists = [0]
    for i in range(1, len(points)):
        d = np.linalg.norm(np.array(points[i]) - np.array(points[i - 1]))
        dists.append(dists[-1] + d)

    total_length = dists[-1]
    num_points = int(total_length // spacing)
    sample_dists = np.linspace(0, total_length, num_points)

    interp_points = []
    for sd in sample_dists:
        for i in range(1, len(points)):
            if dists[i] >= sd:
                t = (sd - dists[i - 1]) / (dists[i] - dists[i - 1])
                x = (1 - t) * points[i - 1][0] + t * points[i][0]
                y = (1 - t) * points[i - 1][1] + t * points[i][1]
                interp_points.append((x, y))
                break
    return interp_points

while True:
    display = img_scaled.copy()

    # Draw path lines
    for i, (x, y) in enumerate(points):
        cv2.circle(display, (x, y), 4, (0, 0, 255), -1)
        if i > 0:
            cv2.line(display, points[i - 1], points[i], (0, 255, 0), 2)
        cv2.putText(display, str(i + 1), (x + 6, y - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    cv2.imshow("Define Path", display)
    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'):
        break
    elif key == ord('u') and points:
        removed = points.pop()
        print(f"Removed point {removed}")
    elif key == ord('s') and len(points) >= 2:
        print("Generating evenly spaced flow points...")
        flow_points = interpolate_path(points, spacing)

        # Rescale to original coordinates
        rescaled_flow = [(x / scale, y / scale) for (x, y) in flow_points]

        # Save data
        data = {
            "track_name": "Monkey Meadow",
            "path_corners": [(x / scale, y / scale) for (x, y) in points],
            "flow_points": rescaled_flow
        }
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Saved {len(flow_points)} flow points to {output_path}")

        # --- Show flow visualization ---
        preview = img_scaled.copy()
        for i, (x, y) in enumerate(flow_points):
            color = (0, 100 + int(155 * (i / len(flow_points))), 255)  # gradient color
            cv2.circle(preview, (int(x), int(y)), 5, color, -1)
        for i in range(1, len(flow_points)):
            cv2.line(preview, (int(flow_points[i - 1][0]), int(flow_points[i - 1][1])),
                     (int(flow_points[i][0]), int(flow_points[i][1])), (0, 255, 0), 1)
        cv2.imshow("Flow Preview", preview)
        cv2.waitKey(0)
        break

cv2.destroyAllWindows()
