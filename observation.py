
from dataclasses import dataclass, field
import uuid

from data.enums import BloonsDifficulty, BloonsGamemode, Hero, Tower, Track

@dataclass
class Sensed:
    # Information directly 'known' from the harness
    pass

@dataclass
class Believed:
    # Information we believe to be true, could become desynced
    pass

@dataclass
class Forecast:
    # Upcoming round information
    pass

@dataclass
class Observation:
    # All information available to the planner/executor
    sensed: Sensed
    believed: Believed
    forecast: Forecast

@dataclass
class PlacedTower:
    # One tower/hero that has been placed
    tower: Tower | Hero
    position: tuple[float, float]
    upgrades: dict = field(default_factory=lambda: {"top": 0, "middle": 0, "bottom": 0})
    radius_px: int = 0
    id: uuid.UUID = field(default_factory=uuid.uuid4)


class StepResult:
    # Any resulting information required after an execution step
    pass

class GameSetup:
    # The configuration state of the game to be applied on reset
    track: Track
    difficulty: BloonsDifficulty
    game_mode: BloonsGamemode
    hero: Hero
