"""Handwritten Monkey Meadow smoke tape for executor / SimulatedHarness."""

from actions import PlaceHero, PlaceTower, Plan, StartRound, Upgrade
from data.enums import (
    BloonsDifficulty,
    BloonsGamemode,
    Hero,
    Tower,
    Track,
    UpgradePath,
)
from observation import GameSetup

SETUP = GameSetup(
    track=Track.MONKEY_MEADOW,
    difficulty=BloonsDifficulty.HARD,
    gamemode=BloonsGamemode.HARD_STANDARD,
    hero=Hero.SAUDA,
)

SAUDA_POS = (0.42, 0.38)
DART_POS = (0.50, 0.38)

PLAN: Plan = [
    PlaceHero(SAUDA_POS, ref="sauda"),
    StartRound(),
    StartRound(),
    PlaceTower(Tower.DART_MONKEY, DART_POS, ref="dart"),
    StartRound(),
    Upgrade(ref="dart", upgrade_path=UpgradePath.TOP),
    StartRound(),
]
