from abc import ABC
from dataclasses import dataclass

from data.enums import Tower, UpgradePath


class Action(ABC):
    # Base "request" for the harness to interpret; should not "do" anything
    ...


@dataclass(frozen=True)
class PlaceTower(Action):
    tower: Tower
    position: tuple[float, float]
    ref: str


@dataclass(frozen=True)
class PlaceHero(Action):
    position: tuple[float, float]
    ref: str


@dataclass(frozen=True)
class Upgrade(Action):
    ref: str
    upgrade_path: UpgradePath


@dataclass(frozen=True)
class Wait(Action):
    pass


@dataclass(frozen=True)
class StartRound(Action):
    pass


Plan = list[Action]
