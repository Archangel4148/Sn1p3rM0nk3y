from dataclasses import dataclass, field
import uuid

from data.enums import (
    BloonsDifficulty,
    BloonsGamemode,
    BloonsScreen,
    Hero,
    Tower,
    Track,
    UpgradePath,
)
from data.rounds_data import RoundData


@dataclass(frozen=True)
class PlacedTower:
    # One tower/hero that we believe is on the map
    tower: Tower | Hero
    position: tuple[float, float]
    upgrades: dict[UpgradePath, int] = field(
        default_factory=lambda: {
            UpgradePath.TOP: 0,
            UpgradePath.MIDDLE: 0,
            UpgradePath.BOTTOM: 0,
        }
    )
    radius_px: int = 0
    id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class Sensed:
    # "Real" data we receive from the Harness
    screen: BloonsScreen
    play_idle: bool
    last_step_ok: bool


@dataclass(frozen=True)
class Believed:
    # Internal approximation of the state (may drift from reality)
    track: Track
    gamemode: BloonsGamemode
    hero: Hero
    round_index: int
    cash: float
    placed: tuple[PlacedTower, ...]
    hero_placed: bool


@dataclass(frozen=True)
class Forecast:
    # Upcoming round information (from data, not vision)
    remaining: tuple[RoundData, ...]


@dataclass(frozen=True)
class Observation:
    # Everything a planner or executor is allowed to know
    sensed: Sensed
    believed: Believed
    forecast: Forecast


@dataclass(frozen=True)
class GameSetup:
    # The configuration of the game, used during execution reset
    track: Track
    difficulty: BloonsDifficulty
    gamemode: BloonsGamemode
    hero: Hero


@dataclass(frozen=True)
class StepResult:
    # Data/result returned after a harness step
    ok: bool
    observation: Observation
    error: str | None = None
    placed_id: uuid.UUID | None = None


@dataclass(frozen=True)
class PlacementCandidate:
    # A potential position to place a tower (comes from Harness)
    position: tuple[float, float]
    flow_points_in_range: int
