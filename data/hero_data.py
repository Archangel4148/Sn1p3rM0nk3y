from dataclasses import dataclass
from pathlib import Path
import json

from data.enums import BloonsDifficulty, Hero


@dataclass
class HeroData:
    hero: Hero
    placement_type: str
    footprint_shape: str
    base_range: float
    base_costs: tuple[float, float, float, float]
    footprint_radius: float | None = None
    category: str | None = None

    def cost(self, difficulty: BloonsDifficulty) -> float:
        return self.base_costs[difficulty.value]

    @classmethod
    def from_dict(cls, hero: Hero, data: dict) -> "HeroData":
        return cls(
            hero=hero,
            placement_type=data["placement_type"],
            footprint_shape=data["footprint_shape"],
            base_range=data["base_range"],
            base_costs=tuple(data["base_costs"]),
            footprint_radius=data.get("footprint_radius"),
            category=data.get("category"),
        )


class HeroDatabase:
    RAW_JSON_PATH = Path(__file__).parent / "tables" / "heroes.json"

    def __init__(self):
        self._data = self.load_hero_data()

    def load_hero_data(self) -> dict[Hero, HeroData]:
        with open(self.RAW_JSON_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        parsed = {}
        for name, blob in raw.items():
            hero = Hero(name)
            parsed[hero] = HeroData.from_dict(hero, blob)
        return parsed

    def get_hero_data(self, hero: Hero) -> HeroData | None:
        return self._data.get(hero)


if __name__ == "__main__":
    db = HeroDatabase()
    print(db.get_hero_data(Hero.SAUDA))
