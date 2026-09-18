from abc import ABC
import uuid

from data.enums import Tower, UpgradePath


class Action(ABC):
    pass


class PlaceTower(Action):
    tower: Tower
    position: tuple[float, float]


class PlaceHero(Action):
    position: tuple[float, float]


class Upgrade(Action):
    tower_id: uuid.UUID
    upgrade_path: UpgradePath


class Wait(Action):
    pass


class StartRound(Action):
    pass
