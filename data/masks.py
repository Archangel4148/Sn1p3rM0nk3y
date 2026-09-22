"""Runtime mask helpers. Pillow + numpy only — no OpenCV in the bot path."""

from pathlib import Path

import numpy as np
from PIL import Image


def load_mask(path: Path) -> np.ndarray:
    """Load a placement/track mask PNG as HxW uint8 (0 or 255-ish)."""
    try:
        image = Image.open(path)
    except OSError as exc:
        raise RuntimeError(f"Could not load mask: {path}") from exc
    return np.asarray(image.convert("L"), dtype=np.uint8)


def stamp_disk(mask: np.ndarray, cx: int, cy: int, radius: int, value: int = 255) -> None:
    """Fill a disk on a 2D occupancy mask (in place)."""
    if radius <= 0:
        return
    h, w = mask.shape[:2]
    y0, y1 = max(cy - radius, 0), min(cy + radius + 1, h)
    x0, x1 = max(cx - radius, 0), min(cx + radius + 1, w)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    disk = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius ** 2
    mask[y0:y1, x0:x1][disk] = value


def mask_or(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.maximum(a, b)
