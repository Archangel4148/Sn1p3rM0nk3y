from enum import IntEnum, StrEnum


class BloonsDifficulty(IntEnum):
    EASY = 0
    MEDIUM = 1
    HARD = 2
    IMPOPPABLE = 3  # Technically not a difficulty, but has its own cost index


class BloonsGamemode(StrEnum):
    EASY_STANDARD = "Easy Standard"
    PRIMARY_ONLY = "Primary Only"
    DEFLATION = "Deflation"
    EASY_SANDBOX = "Easy Sandbox"
    MEDIUM_STANDARD = "Medium Standard"
    MILITARY_ONLY = "Military Only"
    APOPALYPSE = "Apopalypse"
    REVERSE = "Reverse"
    MEDIUM_SANDBOX = "Medium Sandbox"
    HARD_SANDBOX = "Hard Sandbox"
    HARD_STANDARD = "Hard Standard"
    MAGIC_MONKEYS_ONLY = "Magic Monkeys Only"
    DOUBLE_HP_MOABS = "Double HP MOABs"
    HALF_CASH = "Half Cash"
    ALTERNATE_BLOONS_ROUNDS = "Alternate Bloons Rounds"
    IMPOPPABLE = "Impoppable"
    CHIMPS = "CHIMPS"


class Tower(StrEnum):
    ALCHEMIST = "Alchemist"
    BANANA_FARM = "Banana Farm"
    BEAST_HANDLER = "Beast Handler"
    BOMB_SHOOTER = "Bomb Shooter"
    BOOMERANG_MONKEY = "Boomerang Monkey"
    DART_MONKEY = "Dart Monkey"
    DARTLING_GUNNER = "Dartling Gunner"
    DESPERADO = "Desperado"
    DRUID = "Druid"
    ENGINEER_MONKEY = "Engineer Monkey"
    GLUE_GUNNER = "Glue Gunner"
    HELI_PILOT = "Heli Pilot"
    ICE_MONKEY = "Ice Monkey"
    MERMONKEY = "Mermonkey"
    MONKEY_ACE = "Monkey Ace"
    MONKEY_BUCCANEER = "Monkey Buccaneer"
    MONKEY_SUB = "Monkey Sub"
    MONKEY_VILLAGE = "Monkey Village"
    MORTAR_MONKEY = "Mortar Monkey"
    NINJA_MONKEY = "Ninja Monkey"
    SNIPER_MONKEY = "Sniper Monkey"
    SPIKE_FACTORY = "Spike Factory"
    SUPER_MONKEY = "Super Monkey"
    TACK_SHOOTER = "Tack Shooter"
    WIZARD_MONKEY = "Wizard Monkey"


class Hero(StrEnum):
    QUINCY = "Quincy"
    GWENDOLIN = "Gwendolin"
    STRIKER_JONES = "Striker Jones"
    OBYN_GREENFOOT = "Obyn Greenfoot"
    CAPTAIN_CHURCHILL = "Captain Churchill"
    BENJAMIN = "Benjamin"
    EZILI = "Ezili"
    PAT_FUSTY = "Pat Fusty"
    ADORA = "Adora"
    ADMIRAL_BRICKELL = "Admiral Brickell"
    ETIENNE = "Etienne"
    SAUDA = "Sauda"
    PSI = "Psi"
    GERALDO = "Geraldo"
    CORVUS = "Corvus"
    ROSALIA = "Rosalia"
    SILAS = "Silas"


class Track(StrEnum):
    # Beginner
    ALPINE_RUN = "Alpine Run"
    CANDY_FALLS = "Candy Falls"
    CARVED = "Carved"
    CUBISM = "Cubism"
    END_OF_THE_ROAD = "End Of The Road"
    FOUR_CIRCLES = "Four Circles"
    FROZEN_OVER = "Frozen Over"
    HEDGE = "Hedge"
    IN_THE_LOOP = "In The Loop"
    LOGS = "Logs"
    LOTUS_ISLAND = "Lotus Island"
    MIDDLE_OF_THE_ROAD = "Middle of the Road"
    MONKEY_MEADOW = "Monkey Meadow"
    ONE_TWO_TREE = "One Two Tree"
    PARK_PATH = "Park Path"
    RESORT = "Resort"
    SCRAPYARD = "Scrapyard"
    SKATES = "Skates"
    SPA_PITS = "Spa Pits"
    THE_CABIN = "The Cabin"
    THREE_MINES_ROUND = "Three Mines Round"
    TINKERTON = "Tinkerton"
    TOWN_CENTER = "Town Center"
    TREE_STUMP = "Tree Stump"
    WINTER_PARK = "Winter Park"
    # Intermediate
    ADORAS_TEMPLE = "Adora's Temple"
    BALANCE = "Balance"
    BAZAAR = "Bazaar"
    BLOONARIUS_PRIME = "Bloonarius Prime"
    CHUTES = "Chutes"
    COVERED_GARDEN = "Covered Garden"
    CRACKED = "Cracked"
    DOWNSTREAM = "Downstream"
    ENCRYPTED = "Encrypted"
    FIRING_RANGE = "Firing Range"
    HAUNTED = "Haunted"
    KARTSNDARTS = "KartsNDarts"
    LOST_CREVASSE = "Lost Crevasse"
    LUMINOUS_COVE = "Luminous Cove"
    MOON_LANDING = "Moon Landing"
    POLYPHEMUS = "Polyphemus"
    QUARRY = "Quarry"
    QUIET_STREET = "Quiet Street"
    RAKE = "Rake"
    SPICE_ISLANDS = "Spice Islands"
    SPRING_SPRING = "Spring Spring"
    STREAMBED = "Streambed"
    SULFUR_SPRINGS = "Sulfur Springs"
    WATER_PARK = "Water Park"
    # Advanced
    ANCIENT_PORTAL = "Ancient Portal"
    ANOTHER_BRICK = "Another Brick"
    CARGO = "Cargo"
    CASTLE_REVENGE = "Castle Revenge"
    CORNFIELD = "Cornfield"
    DARK_PATH = "Dark Path"
    ENCHANTED_GLADE = "Enchanted Glade"
    EROSION = "Erosion"
    GEARED = "Geared"
    HIGH_FINANCE = "High Finance"
    LAST_RESORT = "Last Resort"
    MESA = "Mesa"
    MIDNIGHT_MANSION = "Midnight Mansion"
    OFF_THE_COAST = "Off The Coast"
    PATS_POND = "Pat's Pond"
    PENINSULA = "Peninsula"
    SPILLWAY = "Spillway"
    SUNKEN_COLUMNS = "Sunken Columns"
    SUNSET_GULCH = "Sunset Gulch"
    UNDERGROUND = "Underground"
    X_FACTOR = "X Factor"
    # Expert
    OUCH = "Ouch"
    BLOODY_PUDDLES = "Bloody Puddles"
    DARK_CASTLE = "Dark Castle"
    DARK_DUNGEONS = "Dark Dungeons"
    FLOODED_VALLEY = "Flooded Valley"
    GLACIAL_TRAIL = "Glacial Trail"
    INFERNAL = "Infernal"
    MUDDY_PUDDLES = "Muddy Puddles"
    QUAD = "Quad"
    RAVINE = "Ravine"
    SANCTUARY = "Sanctuary"
    WORKSHOP = "Workshop"


class DamageType(StrEnum):
    NORMAL = "Normal"
    PLASMA = "Plasma"
    FRIGID = "Frigid"
    EXPLOSION = "Explosion"
    SHATTER = "Shatter"
    GLACIER = "Glacier"
    ENERGY = "Energy"
    SHARP = "Sharp"
    COLD = "Cold"


class CoverageType(StrEnum):
    CAMO = "Camo"
    BLACK = "Black"
    WHITE = "White"
    LEAD = "Lead"
    FROZEN = "Frozen"
    PURPLE = "Purple"


COVERAGE_RATIOS = {
    CoverageType.CAMO: 0.25,
    CoverageType.LEAD: 0.25,
    CoverageType.PURPLE: 0.2,
    CoverageType.WHITE: 0.1,
    CoverageType.BLACK: 0.1,
    CoverageType.FROZEN: 0.2,
}

DAMAGE_TYPE_BY_COVERAGE = {
    DamageType.NORMAL: (CoverageType.BLACK, CoverageType.WHITE, CoverageType.LEAD, CoverageType.FROZEN,
                        CoverageType.PURPLE),
    DamageType.PLASMA: (CoverageType.BLACK, CoverageType.WHITE, CoverageType.LEAD, CoverageType.FROZEN),
    DamageType.FRIGID: (CoverageType.BLACK, CoverageType.LEAD, CoverageType.FROZEN),
    DamageType.EXPLOSION: (CoverageType.WHITE, CoverageType.LEAD, CoverageType.FROZEN, CoverageType.PURPLE),
    DamageType.SHATTER: (CoverageType.BLACK, CoverageType.WHITE, CoverageType.FROZEN, CoverageType.PURPLE),
    DamageType.GLACIER: (CoverageType.BLACK, CoverageType.LEAD, CoverageType.FROZEN, CoverageType.PURPLE),
    DamageType.ENERGY: (CoverageType.BLACK, CoverageType.WHITE, CoverageType.FROZEN),
    DamageType.SHARP: (CoverageType.BLACK, CoverageType.WHITE, CoverageType.PURPLE),
    DamageType.COLD: (CoverageType.BLACK, CoverageType.FROZEN, CoverageType.PURPLE),
}


class BloonsScreen(StrEnum):
    MAIN_MENU = "Main Menu"
    MAP_SELECT = "Map Select"
    IN_GAME = "In Game"
    PAUSE_MENU = "Pause Menu"
    RESTART_POPUP = "Restart Popup"
    SANDBOX_START_POPUP = "Sandbox Start Popup"
    SANDBOX_BLOON_SCREEN = "In Game Sandbox (Bloon Screen)"
    SANDBOX_MONKEY_SCREEN = "In Game Sandbox (Monkey Screen)"
    GAME_OVER_SCREEN_1 = "Game Over Screen 1"
    GAME_OVER_SCREEN_2 = "Game Over Screen 2"


class BloonsMapLevel(StrEnum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"
    EXPERT = "Expert"


TOWER_HOTKEYS = {
    Tower.ALCHEMIST: "f",
    Tower.BANANA_FARM: "j",
    Tower.BEAST_HANDLER: "o",
    Tower.BOMB_SHOOTER: "e",
    Tower.BOOMERANG_MONKEY: "w",
    Tower.DART_MONKEY: "q",
    Tower.DARTLING_GUNNER: "m",
    Tower.DESPERADO: "u",
    Tower.DRUID: "g",
    Tower.ENGINEER_MONKEY: "i",
    Tower.GLUE_GUNNER: "y",
    Tower.HELI_PILOT: "b",
    Tower.ICE_MONKEY: "t",
    Tower.MERMONKEY: "h",
    Tower.MONKEY_ACE: "v",
    Tower.MONKEY_BUCCANEER: "c",
    Tower.MONKEY_SUB: "x",
    Tower.MONKEY_VILLAGE: "l",
    Tower.MORTAR_MONKEY: "n",
    Tower.NINJA_MONKEY: "d",
    Tower.SNIPER_MONKEY: "z",
    Tower.SPIKE_FACTORY: "k",
    Tower.SUPER_MONKEY: "s",
    Tower.TACK_SHOOTER: "r",
    Tower.WIZARD_MONKEY: "a",
}

UPGRADE_HOTKEYS = {
    "top": ",",
    "middle": ".",
    "bottom": "/",
}

TRACK_THUMBNAIL_LOCATIONS = {
    # Beginner
    Track.ALPINE_RUN: (3, 0),
    Track.CANDY_FALLS: (2, 2),
    Track.CARVED: (2, 4),
    Track.CUBISM: (3, 2),
    Track.END_OF_THE_ROAD: (3, 5),
    Track.FOUR_CIRCLES: (3, 3),
    Track.FROZEN_OVER: (3, 1),
    Track.HEDGE: (3, 4),
    Track.IN_THE_LOOP: (0, 1),
    Track.LOGS: (4, 0),
    Track.LOTUS_ISLAND: (2, 1),
    Track.MIDDLE_OF_THE_ROAD: (1, 1),
    Track.MONKEY_MEADOW: (0, 0),
    Track.ONE_TWO_TREE: (1, 2),
    Track.PARK_PATH: (2, 5),
    Track.RESORT: (1, 5),
    Track.SCRAPYARD: (1, 3),
    Track.SKATES: (2, 0),
    Track.SPA_PITS: (0, 3),
    Track.THE_CABIN: (1, 4),
    Track.THREE_MINES_ROUND: (0, 2),
    Track.TINKERTON: (0, 4),
    Track.TOWN_CENTER: (1, 0),
    Track.TREE_STUMP: (0, 5),
    Track.WINTER_PARK: (2, 3),
    # Intermediate
    Track.ADORAS_TEMPLE: (7, 0),
    Track.BALANCE: (6, 3),
    Track.BAZAAR: (6, 5),
    Track.BLOONARIUS_PRIME: (6, 2),
    Track.CHUTES: (8, 3),
    Track.COVERED_GARDEN: (5, 5),
    Track.CRACKED: (8, 1),
    Track.DOWNSTREAM: (7, 5),
    Track.ENCRYPTED: (6, 4),
    Track.FIRING_RANGE: (8, 0),
    Track.HAUNTED: (7, 4),
    Track.KARTSNDARTS: (7, 2),
    Track.LOST_CREVASSE: (5, 0),
    Track.LUMINOUS_COVE: (5, 1),
    Track.MOON_LANDING: (7, 3),
    Track.POLYPHEMUS: (5, 4),
    Track.QUARRY: (6, 0),
    Track.QUIET_STREET: (6, 1),
    Track.RAKE: (8, 4),
    Track.SPICE_ISLANDS: (8, 5),
    Track.SPRING_SPRING: (7, 1),
    Track.STREAMBED: (8, 2),
    Track.SULFUR_SPRINGS: (5, 2),
    Track.WATER_PARK: (5, 3),
    # Advanced
    Track.ANCIENT_PORTAL: (9, 3),
    Track.ANOTHER_BRICK: (11, 5),
    Track.CARGO: (11, 1),
    Track.CASTLE_REVENGE: (9, 4),
    Track.CORNFIELD: (12, 1),
    Track.DARK_PATH: (9, 5),
    Track.ENCHANTED_GLADE: (9, 1),
    Track.EROSION: (10, 0),
    Track.GEARED: (10, 5),
    Track.HIGH_FINANCE: (11, 4),
    Track.LAST_RESORT: (9, 2),
    Track.MESA: (10, 4),
    Track.MIDNIGHT_MANSION: (10, 1),
    Track.OFF_THE_COAST: (12, 0),
    Track.PATS_POND: (11, 2),
    Track.PENINSULA: (11, 3),
    Track.SPILLWAY: (11, 0),
    Track.SUNKEN_COLUMNS: (10, 2),
    Track.SUNSET_GULCH: (9, 0),
    Track.UNDERGROUND: (12, 2),
    Track.X_FACTOR: (10, 3),
    # Expert
    Track.OUCH: (14, 5),
    Track.BLOODY_PUDDLES: (14, 0),
    Track.DARK_CASTLE: (14, 3),
    Track.DARK_DUNGEONS: (13, 1),
    Track.FLOODED_VALLEY: (13, 4),
    Track.GLACIAL_TRAIL: (13, 0),
    Track.INFERNAL: (13, 5),
    Track.MUDDY_PUDDLES: (14, 4),
    Track.QUAD: (14, 2),
    Track.RAVINE: (13, 3),
    Track.SANCTUARY: (13, 2),
    Track.WORKSHOP: (14, 1),
}

# Unique identifier points for each screen
PAGE_IDENTIFIER_POINTS = {
    BloonsScreen.MAIN_MENU: [[((0.5, 0.875), (255, 255, 255)), ((0.957, 0.043), (255, 220, 0))]],
    BloonsScreen.MAP_SELECT: [[((0.298, 0.901), (255, 197, 0)), ((0.948, 0.077), (0, 195, 255))]],
    BloonsScreen.IN_GAME: [[((0.878, 0.919), (255, 222, 0)), ((0.880, 0.960), (255, 207, 0)),
                            ((0.904, 0.935), (255, 217, 0)), ((0.897, 0.968), (255, 196, 0)),
                            ((0.892, 0.952), (255, 255, 255)), ((0.890, 0.925), (255, 255, 255)),
                            ((0.149, 0.038), (255, 187, 0)), ((0.881, 0.056), (59, 214, 0))]],
    BloonsScreen.PAUSE_MENU: [[((0.341, 0.747), (0, 221, 255))]],
    BloonsScreen.RESTART_POPUP: [[((0.264, 0.331), (255, 195, 0)), ((0.588, 0.371), (113, 232, 0))]],
    BloonsScreen.SANDBOX_START_POPUP: [[((0.468, 0.705), (93, 225, 0)), ((0.501, 0.255), (255, 204, 68)),
                                        ((0.164, 0.017), (255, 199, 0))]],
    BloonsScreen.SANDBOX_BLOON_SCREEN: [[((0.823, 0.697), (0, 221, 255)), ((0.822, 0.806), (255, 196, 0)),
                                         ((0.823, 0.858), (255, 121, 0)), ((0.822, 0.947), (255, 116, 0)),
                                         ((0.148, 0.047), (255, 162, 0)), ((0.943, 0.104), (84, 222, 0))],
                                        [((0.872, 0.914), (0, 212, 245)), ((0.871, 0.967), (0, 190, 245)),
                                         ((0.909, 0.909), (0, 212, 245)), ((0.911, 0.968), (0, 188, 245)),
                                         ((0.899, 0.931), (245, 245, 245)), ((0.883, 0.922), (245, 245, 245)),
                                         ((0.877, 0.956), (245, 245, 245))]],
    BloonsScreen.SANDBOX_MONKEY_SCREEN: [[((0.874, 0.915), (245, 212, 0)), ((0.907, 0.914), (245, 212, 0)),
                                          ((0.873, 0.944), (245, 203, 0)), ((0.909, 0.944), (245, 203, 0)),
                                          ((0.902, 0.944), (244, 244, 244)), ((0.880, 0.942), (245, 245, 245)),
                                          ((0.891, 0.914), (245, 245, 245))],
                                         [((0.875, 0.913), (255, 221, 0)), ((0.882, 0.924), (255, 255, 255)),
                                          ((0.874, 0.961), (255, 201, 0)), ((0.882, 0.947), (255, 255, 255)),
                                          ((0.901, 0.925), (254, 254, 254)), ((0.908, 0.910), (255, 221, 0)),
                                          ((0.148, 0.037), (255, 187, 0)), ((0.881, 0.048), (77, 220, 0))]
                                         ],
    BloonsScreen.GAME_OVER_SCREEN_1: [[((0.325, 0.180), (255, 60, 0)), ((0.472, 0.185), (255, 56, 0)),
                                       ((0.654, 0.177), (255, 62, 0)), ((0.539, 0.843), (102, 228, 0))]],
    BloonsScreen.GAME_OVER_SCREEN_2: [[((0.469, 0.154), (163, 81, 33)), ((0.331, 0.337), (255, 38, 0)),
                                       ((0.668, 0.324), (255, 48, 0)), ((0.665, 0.711), (113, 232, 0)),
                                       ((0.554, 0.706), (0, 221, 255)), ((0.443, 0.707), (255, 221, 0)),
                                       ((0.327, 0.706), (0, 221, 255))]],
}
SELECTED_MAP_SELECT_TAB_COLOR = (64, 159, 255)
MAP_SELECT_PAGE_POINTS = [
    (0.365, 0.703),
    (0.384, 0.703),
    (0.404, 0.703),
    (0.423, 0.703),
    (0.443, 0.703),
    (0.462, 0.703),
    (0.481, 0.703),
    (0.500, 0.703),
    (0.519, 0.703),
    (0.539, 0.703),
    (0.558, 0.703),
    (0.578, 0.703),
    (0.597, 0.703),
    (0.616, 0.703),
    (0.635, 0.703),
]
MAP_SELECT_THUMBNAIL_POSITIONS = [
    (0.280, 0.240),
    (0.505, 0.240),
    (0.730, 0.240),
    (0.280, 0.533),
    (0.505, 0.533),
    (0.730, 0.533),
]
MAP_SELECT_MAP_LEVEL_POSITIONS = {
    BloonsMapLevel.BEGINNER: (0.303, 0.906),
    BloonsMapLevel.INTERMEDIATE: (0.435, 0.906),
    BloonsMapLevel.ADVANCED: (0.566, 0.906),
    BloonsMapLevel.EXPERT: (0.697, 0.906),
}
MAP_SELECT_RIGHT_ARROW_POSITION = (0.856, 0.400)
MAP_SELECT_LEFT_ARROW_POSITION = (0.144, 0.400)
DIFFICULTY_SELECT_POSITIONS = {
    BloonsDifficulty.EASY: (0.327, 0.375),
    BloonsDifficulty.MEDIUM: (0.504, 0.375),
    BloonsDifficulty.HARD: (0.673, 0.375),
}
GAMEMODE_SELECT_POSITIONS = {
    BloonsDifficulty.EASY: {
        BloonsGamemode.EASY_STANDARD: (0.331, 0.552),
        BloonsGamemode.PRIMARY_ONLY: (0.499, 0.425),
        BloonsGamemode.DEFLATION: (0.672, 0.423),
        BloonsGamemode.EASY_SANDBOX: (0.503, 0.692),
    },
    BloonsDifficulty.MEDIUM: {
        BloonsGamemode.MEDIUM_STANDARD: (0.331, 0.552),
        BloonsGamemode.MILITARY_ONLY: (0.503, 0.422),
        BloonsGamemode.APOPALYPSE: (0.672, 0.419),
        BloonsGamemode.REVERSE: (0.501, 0.693),
        BloonsGamemode.MEDIUM_SANDBOX: (0.674, 0.685),
    },
    BloonsDifficulty.HARD: {
        BloonsGamemode.HARD_STANDARD: (0.331, 0.556),
        BloonsGamemode.HARD_SANDBOX: (0.160, 0.544),
        BloonsGamemode.MAGIC_MONKEYS_ONLY: (0.498, 0.418),
        BloonsGamemode.DOUBLE_HP_MOABS: (0.665, 0.417),
        BloonsGamemode.HALF_CASH: (0.836, 0.413),
        BloonsGamemode.ALTERNATE_BLOONS_ROUNDS: (0.499, 0.688),
        BloonsGamemode.IMPOPPABLE: (0.668, 0.688),
        BloonsGamemode.CHIMPS: (0.838, 0.684),
    }
}

SCREEN_TRANSITIONS = {
    BloonsScreen.MAIN_MENU: {
        BloonsScreen.MAP_SELECT: {
            "action": "click",
            "pos": (0.5, 0.875),
        }
    },
    BloonsScreen.MAP_SELECT: {
        BloonsScreen.IN_GAME: {
            "action": "custom"
        },
        BloonsScreen.SANDBOX_START_POPUP: {
            "action": "custom"
        },
        BloonsScreen.MAIN_MENU: {
            "action": "click",
            "pos": (0.040, 0.052),
        }
    },
    BloonsScreen.IN_GAME: {
        BloonsScreen.PAUSE_MENU: {
            "action": "key",
            "key": "esc",
        },
    },
    BloonsScreen.PAUSE_MENU: {
        BloonsScreen.MAIN_MENU: {
            "action": "click",
            "pos": (0.441, 0.781),
        },
        BloonsScreen.RESTART_POPUP: {
            "action": "click",
            "pos": (0.559, 0.781),
        },
        BloonsScreen.IN_GAME: {
            "action": "click",
            "pos": (0.678, 0.781),
        }
    },
    BloonsScreen.RESTART_POPUP: {
        BloonsScreen.IN_GAME: {
            "action": "click",
            "pos": (0.409, 0.677),
        }
    },
    BloonsScreen.SANDBOX_START_POPUP: {
        BloonsScreen.SANDBOX_BLOON_SCREEN: {
            "action": "click",
            "pos": (0.502, 0.704),
            "post_delay": 1,
        }
    },
    BloonsScreen.SANDBOX_BLOON_SCREEN: {
        BloonsScreen.SANDBOX_MONKEY_SCREEN: {
            "action": "click",
            "pos": (0.892, 0.946),
        }
    },
    BloonsScreen.SANDBOX_MONKEY_SCREEN: {
        BloonsScreen.SANDBOX_BLOON_SCREEN: {
            "action": "click",
            "pos": (0.892, 0.946),
        }
    },
    BloonsScreen.GAME_OVER_SCREEN_1: {
        BloonsScreen.GAME_OVER_SCREEN_2: {
            "action": "click",
            "pos": (0.5, 0.845),
            "post_delay": 1,
        }
    },
    BloonsScreen.GAME_OVER_SCREEN_2: {
        BloonsScreen.MAIN_MENU: {
            "action": "click",
            "pos": (0.327, 0.749),
            "post_delay": 1,
        }
    }
}
