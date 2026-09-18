from dataclasses import dataclass, field
from pathlib import Path
import json

from data.enums import Track


@dataclass
class TrackData:
    track: Track
    folder: Path
    track_mask: object
    land_mask: object
    water_mask: object
    flow_points: list
    path_corners: list = field(default_factory=list)

    @property
    def size(self) -> tuple[int, int]:
        """(height, width) of the placement masks."""
        h, w = self.land_mask.shape[:2]
        return h, w

    def empty_occupancy(self):
        import numpy as np
        if self.land_mask.ndim == 3:
            return np.zeros_like(self.land_mask[:, :, 0], dtype=np.uint8)
        return np.zeros_like(self.land_mask, dtype=np.uint8)

    @staticmethod
    def folder_name(track: Track) -> str:
        return track.value.lower().replace(" ", "_")

    @classmethod
    def from_folder(cls, track: Track, folder: Path) -> "TrackData":
        import cv2

        track_mask = cv2.imread(str(folder / "track_mask.png"))
        land_mask = cv2.imread(str(folder / "land_placement_mask.png"))
        water_mask = cv2.imread(str(folder / "water_placement_mask.png"))
        if track_mask is None:
            raise RuntimeError(f"Could not load track mask: {folder / 'track_mask.png'}")
        if land_mask is None:
            raise RuntimeError(f"Could not load land placement mask: {folder / 'land_placement_mask.png'}")
        if water_mask is None:
            raise RuntimeError(f"Could not load water placement mask: {folder / 'water_placement_mask.png'}")

        with open(folder / "path_points.json", "r", encoding="utf-8") as f:
            points = json.load(f)
        flow_points = points.get("flow_points") or []
        if not flow_points:
            raise RuntimeError(f"No flow points found in {folder / 'path_points.json'}")

        return cls(
            track=track,
            folder=folder,
            track_mask=track_mask,
            land_mask=land_mask,
            water_mask=water_mask,
            flow_points=flow_points,
            path_corners=points.get("path_corners") or [],
        )


class TrackDatabase:
    ROOT = Path(__file__).parent / "tracks"

    def __init__(self):
        self._cache: dict[Track, TrackData] = {}

    def get_track_data(self, track: Track) -> TrackData | None:
        if track in self._cache:
            return self._cache[track]
        folder = self.ROOT / TrackData.folder_name(track)
        if not folder.is_dir():
            return None
        data = TrackData.from_folder(track, folder)
        self._cache[track] = data
        return data


if __name__ == "__main__":
    db = TrackDatabase()
    meadow = db.get_track_data(Track.MONKEY_MEADOW)
    print(meadow.track, meadow.size, len(meadow.flow_points) if meadow else None)
