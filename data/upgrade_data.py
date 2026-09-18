from dataclasses import dataclass
from pathlib import Path
import json

from data.enums import BloonsDifficulty, Tower, UpgradePath


_PATH_FROM_JSON = {
    1: UpgradePath.TOP,
    2: UpgradePath.MIDDLE,
    3: UpgradePath.BOTTOM,
}


@dataclass
class UpgradeData:
    tower: Tower
    path: UpgradePath
    tier: int
    name: str
    effect: str
    cost: tuple[float, float, float, float]
    grants_camo: bool
    grants_lead: bool
    added_range: float
    cooldown: float | None = None
    range: float | None = None
    pierce: float | None = None
    damage: float | None = None
    damage_type: str | None = None
    projectiles: float | None = None

    def cost_for(self, difficulty: BloonsDifficulty) -> float:
        return self.cost[difficulty.value]

    @classmethod
    def from_dict(cls, tower: Tower, data: dict) -> "UpgradeData":
        return cls(
            tower=tower,
            path=_PATH_FROM_JSON[data["path"]],
            tier=data["tier"],
            name=data["name"],
            effect=data["effect"],
            cost=tuple(data["cost"]),
            grants_camo=data["grants_camo"],
            grants_lead=data["grants_lead"],
            added_range=data["added_range"],
            cooldown=data.get("Cooldown"),
            range=data.get("Range"),
            pierce=data.get("Pierce"),
            damage=data.get("Damage"),
            damage_type=data.get("Damage Type"),
            projectiles=data.get("Projectiles"),
        )


class UpgradeDatabase:
    RAW_JSON_PATH = Path(__file__).parent / "tables" / "upgrades.json"

    def __init__(self):
        self._data = self.load_upgrade_data()

    def load_upgrade_data(self) -> dict[Tower, list[UpgradeData]]:
        with open(self.RAW_JSON_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        parsed = {}
        for name, blobs in raw.items():
            tower = Tower(name)
            parsed[tower] = [UpgradeData.from_dict(tower, blob) for blob in blobs]
        return parsed

    def get_upgrades(self, tower: Tower) -> list[UpgradeData]:
        return list(self._data.get(tower, []))

    def get_upgrade(self, tower: Tower, path: UpgradePath, tier: int) -> UpgradeData | None:
        for upgrade in self._data.get(tower, []):
            if upgrade.path == path and upgrade.tier == tier:
                return upgrade
        return None

    def get_next_upgrade(self, tower: Tower, path: UpgradePath, current_tier: int) -> UpgradeData | None:
        return self.get_upgrade(tower, path, current_tier + 1)


if __name__ == "__main__":
    db = UpgradeDatabase()
    print(db.get_upgrade(Tower.NINJA_MONKEY, UpgradePath.MIDDLE, 1))
    print(db.get_next_upgrade(Tower.DART_MONKEY, UpgradePath.TOP, 0))
