from abc import ABC, abstractmethod

from actions import Action
from data.enums import Hero, Tower
from observation import GameSetup, Observation, PlacementCandidate, StepResult


class Harness(ABC):
    # The game API. Handles Actions and Observations
    @abstractmethod
    def reset(self, setup: GameSetup) -> Observation:
        ...

    @abstractmethod
    def observe(self) -> Observation:
        ...

    @abstractmethod
    def step(self, action: Action) -> StepResult:
        ...

    def placement_candidates(self, tower: Tower | Hero) -> list[PlacementCandidate]:
        ...


class GameHarness(Harness):
    # Harness for a BTD6 game window

    def reset(self, setup: GameSetup) -> Observation:
        raise NotImplementedError

    def observe(self) -> Observation:
        raise NotImplementedError

    def step(self, action: Action) -> StepResult:
        raise NotImplementedError

class SimulatedHarness(Harness):
    # Simulated Harness to pre-play games (without a game window)

    def reset(self, setup: GameSetup) -> Observation:
        raise NotImplementedError

    def observe(self) -> Observation:
        raise NotImplementedError

    def step(self, action: Action) -> StepResult:
        raise NotImplementedError

    def placement_candidates(self, tower: Tower | Hero) -> list[PlacementCandidate]:
        raise NotImplementedError
