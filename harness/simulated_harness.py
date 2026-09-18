from actions import Action
from data.enums import Hero, Tower
from harness import Harness
from observation import GameSetup, Observation, PlacementCandidate, StepResult

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