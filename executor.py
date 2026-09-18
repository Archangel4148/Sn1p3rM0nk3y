from actions import Action
from harness import Harness
from observation import Observation


class Executor:
    # Executes a provided series of actions onto a Harness
    def run(self, harness: Harness, plan: list[Action]) -> Observation:
        raise NotImplementedError
