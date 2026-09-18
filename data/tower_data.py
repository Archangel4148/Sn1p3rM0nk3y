from dataclasses import dataclass
from pathlib import Path
import json

from data.enums import BloonsDifficulty, Tower


@dataclass
class TowerData:
    tower: Tower
    category: str
    placement_type: str
    footprint_shape: str
    base_range: float
    base_costs: tuple[float, float, float, float]
    base_sees_camo: bool
    base_pops_lead: bool
    footprint_radius: float | None = None
    footprint_width: float | None = None
    footprint_height: float | None = None
    cooldown: float | None = None
    range: float | None = None
    pierce: float | None = None
    damage: float | None = None
    damage_type: str | None = None
    projectiles: float | None = None

    def cost(self, difficulty: BloonsDifficulty) -> float:
        return self.base_costs[difficulty.value]

    @classmethod
    def from_dict(cls, tower: Tower, data: dict) -> "TowerData":
        return cls(
            tower=tower,
            category=data["category"],
            placement_type=data["placement_type"],
            footprint_shape=data["footprint_shape"],
            base_range=data["base_range"],
            base_costs=tuple(data["base_costs"]),
            base_sees_camo=data["base_sees_camo"],
            base_pops_lead=data["base_pops_lead"],
            footprint_radius=data.get("footprint_radius"),
            footprint_width=data.get("footprint_width"),
            footprint_height=data.get("footprint_height"),
            cooldown=data.get("cooldown"),
            range=data.get("range"),
            pierce=data.get("pierce"),
            damage=data.get("damage"),
            damage_type=data.get("damage_type"),
            projectiles=data.get("projectiles"),
        )


class TowerDatabase:
    RAW_JSON_PATH = Path(__file__).parent / "tables" / "towers.json"

    def __init__(self):
        self._data = self.load_tower_data()

    def load_tower_data(self) -> dict[Tower, TowerData]:
        with open(self.RAW_JSON_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        parsed = {}
        for name, blob in raw.items():
            tower = Tower(name)
            parsed[tower] = TowerData.from_dict(tower, blob)
        return parsed

    def get_tower_data(self, tower: Tower) -> TowerData | None:
        return self._data.get(tower)


if __name__ == "__main__":
    db = TowerDatabase()
    print(db.get_tower_data(Tower.DART_MONKEY))
