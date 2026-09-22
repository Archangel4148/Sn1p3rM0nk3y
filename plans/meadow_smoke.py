from actions import PlaceTower, Plan, StartRound, Upgrade
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

DART_POS = (0.50, 0.38)

# Hard: $650 start, dart $215, Sharp Shots $150.
PLAN: Plan = [
    PlaceTower(Tower.DART_MONKEY, DART_POS, ref="dart"),
    StartRound(),
    StartRound(),
    Upgrade(ref="dart", upgrade_path=UpgradePath.TOP),
    StartRound(),
]
