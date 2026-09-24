"""Shared placement sampling for GameHarness and SimulatedHarness."""

from __future__ import annotations

import numpy as np

from catalog import Catalog
from data.enums import Hero, Tower
from data.masks import mask_or
from data.track_data import TrackData
from observation import PlacementCandidate
from system_flags import PIXELS_PER_BLOONS_UNIT


def footprint_radius_px(catalog: Catalog, kind: Tower | Hero) -> int:
    if isinstance(kind, Tower):
        data = catalog.towers.get_tower_data(kind)
    else:
        data = catalog.heroes.get_hero_data(kind)
    if data is None:
        raise KeyError(f"No catalog entry for {kind}")

    if data.footprint_shape == "circular":
        return int((data.footprint_radius or 10) * PIXELS_PER_BLOONS_UNIT)
    if data.footprint_shape == "rectangular":
        width = getattr(data, "footprint_width", None) or 10
        height = getattr(data, "footprint_height", None) or 10
        radius = (width ** 2 + height ** 2) ** 0.5 / 2
        return int(radius * PIXELS_PER_BLOONS_UNIT)
    return int(10 * PIXELS_PER_BLOONS_UNIT)


def attack_range_px(catalog: Catalog, kind: Tower | Hero) -> int:
    if isinstance(kind, Tower):
        data = catalog.towers.get_tower_data(kind)
    else:
        data = catalog.heroes.get_hero_data(kind)
    if data is None:
        raise KeyError(f"No catalog entry for {kind}")
    return int((data.base_range or 0) * PIXELS_PER_BLOONS_UNIT)


def placement_mask(catalog: Catalog, track: TrackData, kind: Tower | Hero):
    if isinstance(kind, Tower):
        data = catalog.towers.get_tower_data(kind)
    else:
        data = catalog.heroes.get_hero_data(kind)
    if data is None:
        raise KeyError(f"No catalog entry for {kind}")

    if data.placement_type == "land":
        return track.land_mask
    if data.placement_type == "water":
        return track.water_mask
    if data.placement_type == "any":
        return mask_or(track.land_mask, track.water_mask)
    raise ValueError(f"Unknown placement type: {data.placement_type}")


def find_placement_candidates(
    catalog: Catalog,
    track: TrackData,
    occupied_mask: np.ndarray,
    kind: Tower | Hero,
    *,
    sample_step: int = 20,
    top_k: int = 8,
    min_flow_points: int = 1,
) -> list[PlacementCandidate]:
    """Scan the map for legal spots, ranked by flow-point coverage."""
    mask = placement_mask(catalog, track, kind)
    tower_r = int(np.ceil(footprint_radius_px(catalog, kind)))
    range_px = attack_range_px(catalog, kind)
    range_sq = float(range_px * range_px)

    flow_pts = np.asarray(track.flow_points, dtype=float)
    if flow_pts.ndim != 2 or flow_pts.shape[1] != 2:
        raise ValueError("Track flow_points must be a list of (x, y) pairs.")

    h, w = mask.shape[:2]
    scored: list[tuple[int, float, float]] = []

    for y in range(0, h, sample_step):
        for x in range(0, w, sample_step):
            if mask[y, x] < 128:
                continue
            if _intersects_track(track.track_mask, x, y, tower_r, w, h):
                continue
            if _overlaps(occupied_mask, x, y, tower_r, w, h):
                continue
            score = int(np.sum((flow_pts[:, 0] - x) ** 2 + (flow_pts[:, 1] - y) ** 2 < range_sq))
            if score < min_flow_points:
                continue
            scored.append((score, x / w, y / h))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        PlacementCandidate(position=(nx, ny), flow_points_in_range=score)
        for score, nx, ny in scored[:top_k]
    ]


def _intersects_track(track_mask, x: int, y: int, radius: int, w: int, h: int) -> bool:
    y0, y1 = max(y - radius, 0), min(y + radius, h)
    x0, x1 = max(x - radius, 0), min(x + radius, w)
    return bool(np.any(track_mask[y0:y1, x0:x1] > 128))


def _overlaps(occupied, x: int, y: int, radius: int, w: int, h: int) -> bool:
    y0, y1 = max(y - radius, 0), min(y + radius, h)
    x0, x1 = max(x - radius, 0), min(x + radius, w)
    return bool(np.any(occupied[y0:y1, x0:x1] > 0))
