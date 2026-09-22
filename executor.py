from actions import Action
from harness import Harness
from observation import Observation
from system_flags import vprint


class Executor:
    def run(self, harness: Harness, plan: list[Action]) -> Observation:
        observation = harness.observe()

        for i, action in enumerate(plan):
            result = harness.step(action)
            observation = result.observation
            if not result.ok:
                vprint(f"Executor stopped at step {i}: {result.error}")
                break

        return observation
