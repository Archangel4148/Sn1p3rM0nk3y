
from abc import ABC, abstractmethod
from observation import GameSetup, Observation, StepResult, PlacementCandidate
from actions import Action
from data.enums import Tower, Hero

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
        """Legal map spots for this tower, ranked by flow-point coverage."""
        ...
