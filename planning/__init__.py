from abc import ABC, abstractmethod

from actions import Action
from catalog import Catalog
from observation import Observation


class Planner(ABC):
    """Offline search. Reads Observation + catalog, returns a plan. No window."""

    @abstractmethod
    def plan(self, observation: Observation, catalog: Catalog) -> list[Action]:
        raise NotImplementedError
