from abc import ABC

from actions import Action


class Harness(ABC):
    def handle_action(self, action: Action):
        pass
