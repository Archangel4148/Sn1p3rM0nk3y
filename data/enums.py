from enum import IntEnum, StrEnum, auto


class BloonsDifficulty(IntEnum):
    EASY = 0
    MEDIUM = 1
    HARD = 2
    IMPOPPABLE = 3  # Technically not a difficulty, but has its own cost index


class BloonsGamemode(StrEnum):
    EASY_STANDARD = auto()
    PRIMARY_ONLY = auto()
    DEFLATION = auto()
    EASY_SANDBOX = auto()
    MEDIUM_STANDARD = auto()
    MILITARY_ONLY = auto()
    APOPALYPSE = auto()
    REVERSE = auto()
    MEDIUM_SANDBOX = auto()
    HARD_SANDBOX = auto()
    HARD_STANDARD = auto()
    MAGIC_MONKEYS_ONLY = auto()
    DOUBLE_HP_MOABS = auto()
    HALF_CASH = auto()
    ALTERNATE_BLOONS_ROUNDS = auto()
    IMPOPPABLE = auto()
    CHIMPS = auto()


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
    PROTECT_THE_YACHT = "Protect The Yacht"
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


class BloonsScreen(StrEnum):
    MAIN_MENU = "Main Menu"
    MAP_SELECT = "Map Select"
    IN_GAME = "In Game"
    PAUSE_MENU = "Pause Menu"
    RESTART_POPUP = "Restart Popup"


# TODO: Update this!
TRACK_THUMBNAIL_LOCATIONS = {
    # Beginner
    Track.ALPINE_RUN: (None, None),
    Track.CANDY_FALLS: (None, None),
    Track.CARVED: (None, None),
    Track.CUBISM: (None, None),
    Track.END_OF_THE_ROAD: (None, None),
    Track.FOUR_CIRCLES: (None, None),
    Track.FROZEN_OVER: (None, None),
    Track.HEDGE: (None, None),
    Track.IN_THE_LOOP: (None, None),
    Track.LOGS: (None, None),
    Track.LOTUS_ISLAND: (None, None),
    Track.MIDDLE_OF_THE_ROAD: (None, None),
    Track.MONKEY_MEADOW: (0, 0),
    Track.ONE_TWO_TREE: (None, None),
    Track.PARK_PATH: (None, None),
    Track.RESORT: (None, None),
    Track.SCRAPYARD: (None, None),
    Track.SKATES: (None, None),
    Track.SPA_PITS: (None, None),
    Track.THE_CABIN: (None, None),
    Track.THREE_MINES_ROUND: (None, None),
    Track.TINKERTON: (None, None),
    Track.TOWN_CENTER: (None, None),
    Track.TREE_STUMP: (None, None),
    Track.WINTER_PARK: (None, None),
    # Intermediate
    Track.ADORAS_TEMPLE: (None, None),
    Track.BALANCE: (None, None),
    Track.BAZAAR: (None, None),
    Track.BLOONARIUS_PRIME: (None, None),
    Track.CHUTES: (None, None),
    Track.COVERED_GARDEN: (None, None),
    Track.CRACKED: (None, None),
    Track.DOWNSTREAM: (None, None),
    Track.ENCRYPTED: (None, None),
    Track.FIRING_RANGE: (None, None),
    Track.HAUNTED: (None, None),
    Track.KARTSNDARTS: (None, None),
    Track.LOST_CREVASSE: (None, None),
    Track.LUMINOUS_COVE: (None, None),
    Track.MOON_LANDING: (None, None),
    Track.POLYPHEMUS: (None, None),
    Track.PROTECT_THE_YACHT: (None, None),
    Track.QUARRY: (None, None),
    Track.QUIET_STREET: (None, None),
    Track.RAKE: (None, None),
    Track.SPICE_ISLANDS: (None, None),
    Track.SPRING_SPRING: (None, None),
    Track.STREAMBED: (None, None),
    Track.SULFUR_SPRINGS: (None, None),
    Track.WATER_PARK: (None, None),
    # Advanced
    Track.ANCIENT_PORTAL: (None, None),
    Track.ANOTHER_BRICK: (None, None),
    Track.CARGO: (None, None),
    Track.CASTLE_REVENGE: (None, None),
    Track.CORNFIELD: (None, None),
    Track.DARK_PATH: (None, None),
    Track.ENCHANTED_GLADE: (None, None),
    Track.EROSION: (None, None),
    Track.GEARED: (None, None),
    Track.HIGH_FINANCE: (None, None),
    Track.LAST_RESORT: (None, None),
    Track.MESA: (None, None),
    Track.MIDNIGHT_MANSION: (None, None),
    Track.OFF_THE_COAST: (None, None),
    Track.PATS_POND: (None, None),
    Track.PENINSULA: (None, None),
    Track.SPILLWAY: (None, None),
    Track.SUNKEN_COLUMNS: (None, None),
    Track.SUNSET_GULCH: (None, None),
    Track.UNDERGROUND: (None, None),
    Track.X_FACTOR: (None, None),
    # Expert
    Track.OUCH: (None, None),
    Track.BLOODY_PUDDLES: (None, None),
    Track.DARK_CASTLE: (None, None),
    Track.DARK_DUNGEONS: (None, None),
    Track.FLOODED_VALLEY: (None, None),
    Track.GLACIAL_TRAIL: (None, None),
    Track.INFERNAL: (None, None),
    Track.MUDDY_PUDDLES: (None, None),
    Track.QUAD: (None, None),
    Track.RAVINE: (None, None),
    Track.SANCTUARY: (None, None),
    Track.WORKSHOP: (None, None),
}

# Unique identifier points for each screen
PAGE_IDENTIFIER_POINTS = {
    BloonsScreen.MAIN_MENU: [((0.5, 0.875), (255, 255, 255)), ((0.957, 0.043), (255, 220, 0))],
    BloonsScreen.MAP_SELECT: [((0.298, 0.901), (255, 197, 0)), ((0.948, 0.077), (0, 195, 255))],
    BloonsScreen.IN_GAME: [((0.969, 0.916), (113, 232, 0)), ((0.982, 0.023), (193, 153, 96))],
    BloonsScreen.PAUSE_MENU: [((0.341, 0.747), (0, 221, 255))],
    BloonsScreen.RESTART_POPUP: [((0.264, 0.331), (255, 195, 0)), ((0.588, 0.371), (113, 232, 0))],
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
            "action": "custom"  # This transition needs special handling
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
        }
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
    }
}
