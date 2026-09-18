from actions import Action
from catalog import Catalog
from observation import Observation
from planning import Planner


class HeuristicPlanner(Planner):
    """v2 checkpoint search. Leave empty until the executor plays a handwritten plan."""

    def plan(self, observation: Observation, catalog: Catalog) -> list[Action]:
        raise NotImplementedError
