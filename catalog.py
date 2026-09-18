from data.enums import (
    STARTING_CASH,
    STARTING_ROUND,
    BloonsDifficulty,
    BloonsGamemode,
    Hero,
    Tower,
    UpgradePath,
)
from data.hero_data import HeroDatabase
from data.rounds_data import RoundData, RoundsDatabase
from data.tower_data import TowerDatabase
from data.track_data import TrackDatabase
from data.upgrade_data import UpgradeDatabase
from observation import PlacedTower


class Catalog:
    """Lookup service. Instantiating one loads every static database."""

    def __init__(self):
        self.rounds = RoundsDatabase()
        self.towers = TowerDatabase()
        self.heroes = HeroDatabase()
        self.upgrades = UpgradeDatabase()
        self.tracks = TrackDatabase()

    def starting_cash(self, gamemode: BloonsGamemode) -> float:
        return STARTING_CASH[gamemode]

    def starting_round(self, gamemode: BloonsGamemode) -> int:
        return STARTING_ROUND[gamemode]

    def cost_place(self, tower: Tower | Hero, difficulty: BloonsDifficulty) -> float:
        """Get the cost to place the provided tower/hero in the provided difficulty"""
        if isinstance(tower, Tower):
            data = self.towers.get_tower_data(tower)
        elif isinstance(tower, Hero):
            data = self.heroes.get_hero_data(tower)
        else:
            raise TypeError(f"Unsupported place target: {type(tower)}")
        if data is None:
            raise KeyError(f"No catalog entry for {tower}")
        return data.cost(difficulty)

    def cost_upgrade(
        self,
        placed: PlacedTower,
        path: UpgradePath,
        difficulty: BloonsDifficulty,
    ) -> float:
        """Get the cost to buy the selected upgrade in the provided difficulty"""
        if not isinstance(placed.tower, Tower):
            raise TypeError(f"{placed.tower} has no upgrade paths")
        upgrade = self.upgrades.get_next_upgrade(
            placed.tower, path, placed.upgrades[path]
        )
        if upgrade is None:
            raise KeyError(f"No next {path.value} upgrade for {placed.tower}")
        return upgrade.cost_for(difficulty)

    def legal_upgrades(self, placed: PlacedTower) -> list[UpgradePath]:
        """Get all legal upgrades that are currently available for purchase"""
        if not isinstance(placed.tower, Tower):
            return []

        legal = []
        for path in UpgradePath:
            current = placed.upgrades[path]
            if current >= 5:
                continue
            if self.upgrades.get_next_upgrade(placed.tower, path, current) is None:
                continue

            others = [placed.upgrades[p] for p in UpgradePath if p != path]
            if current >= 2 and max(others) >= 3:
                continue
            if current == 0 and sum(t > 0 for t in others) >= 2:
                continue
            legal.append(path)
        return legal

    def remaining_rounds(self, from_round: int) -> tuple[RoundData, ...]:
        """Get RoundData for all remaining rounds in the database"""
        return self.rounds.remaining_from(from_round)

    def income_for_round(self, round_index: int, gamemode: BloonsGamemode) -> float | None:
        """Cash credited after the given round finishes. None if that round is not in the table."""
        data = self.rounds.get_round_data(round_index)
        if data is None:
            return None
        cash = float(data.total_cash)
        if gamemode == BloonsGamemode.HALF_CASH:
            cash *= 0.5
        return cash
