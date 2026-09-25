from dataclasses import dataclass
from pathlib import Path
import json

from data.enums import BloonModifier, BloonType

@dataclass
class BloonGroup:
    base_type: BloonType
    modifiers: list[BloonModifier]
    count: int

    @staticmethod
    def _parse_bloon_types(type_string: str) -> tuple[BloonType, list[BloonModifier]]:
        modifiers = [modifier for modifier in BloonModifier if modifier in type_string]
        base = next(t for t in BloonType if t in type_string)
        return base, modifiers

    @classmethod
    def from_dict(cls, data: dict) -> "BloonGroup":
        base_type, modifiers = cls._parse_bloon_types(data["type"])
        return cls(
            base_type=base_type,
            modifiers=modifiers,
            count=data["count"]
        )

@dataclass
class RoundData:
    round_num: int
    bloon_groups: list[BloonGroup]
    rbe: int
    bloon_cash: int
    round_cash: int

    @property
    def total_cash(self) -> int:
        return self.bloon_cash + self.round_cash

    @staticmethod
    def _parse_cash(cash_str: str) -> tuple[int, int]:
        groups = [cash.replace("$", "").replace(",", "") for cash in cash_str.split(" + ")]
        return tuple(map(float, groups))

    @classmethod
    def from_dict(cls, data: dict) -> "RoundData":

        bloon_cash, round_cash = cls._parse_cash(data["cash"])
        groups = [BloonGroup.from_dict(group) for group in data["bloon_groups"]]

        return cls(
            round_num=data["round"],
            bloon_groups= groups,
            rbe=data["rbe"],
            bloon_cash=bloon_cash,
            round_cash=round_cash
        )

class RoundsDatabase:
    RAW_JSON_PATH = Path(__file__).parent / "tables" / "rounds.json"
    def __init__(self):
        self._data = self.load_rounds_data()
        parsed = [RoundData.from_dict(row) for row in self._data]
        self._by_round = {row.round_num: row for row in parsed}
        self._ordered = tuple(sorted(parsed, key=lambda row: row.round_num))

    def load_rounds_data(self) -> dict:
        with open(self.RAW_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f, parse_int=int)

    def get_round_data(self, round: int) -> RoundData | None:
        return self._by_round.get(round)

    def remaining_from(self, from_round: int) -> tuple[RoundData, ...]:
        return tuple(row for row in self._ordered if row.round_num >= from_round)

if __name__ == "__main__":
    db = RoundsDatabase()
    print(db.get_round_data(140))
