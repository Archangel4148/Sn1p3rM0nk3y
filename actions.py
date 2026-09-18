from abc import ABC
from dataclasses import dataclass
import uuid

from data.enums import Tower, UpgradePath


class Action(ABC):
    # Base "request" for the harness to interpret; should not "do" anything
    ...
    
@dataclass(frozen=True)
class PlaceTower(Action):
    tower: Tower
    position: tuple[float, float]


@dataclass(frozen=True)
class PlaceHero(Action):
    position: tuple[float, float]


@dataclass(frozen=True)
class Upgrade(Action):
    tower_id: uuid.UUID
    upgrade_path: UpgradePath


@dataclass(frozen=True)
class Wait(Action):
    pass


@dataclass(frozen=True)
class StartRound(Action):
    pass


Plan = list[Action]
