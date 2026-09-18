from data.enums import BloonsDifficulty, BloonsGamemode, Hero, Tower, UpgradePath
from data.rounds_data import RoundData
from observation import PlacedTower


class Catalog:
    # Lookup service to get data from available databases
    def starting_cash(self, gamemode: BloonsGamemode) -> float:
        raise NotImplementedError

    def cost_place(self, tower: Tower | Hero, difficulty: BloonsDifficulty) -> float:
        raise NotImplementedError

    def cost_upgrade(self, placed: PlacedTower, path: UpgradePath, difficulty: BloonsDifficulty) -> float:
        raise NotImplementedError

    def legal_upgrades(self, placed: PlacedTower) -> list[UpgradePath]:
        raise NotImplementedError

    def remaining_rounds(self, from_round: int) -> tuple[RoundData, ...]:
        raise NotImplementedError
