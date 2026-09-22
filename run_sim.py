"""Run the Meadow smoke plan against SimulatedHarness (no BTD6 window)."""

from executor import Executor
from harness.simulated_harness import SimulatedHarness
from plans.meadow_smoke import PLAN, SETUP
from system_flags import vprint


def main() -> None:
    harness = SimulatedHarness()
    obs = harness.reset(SETUP)
    vprint(
        f"Start: round {obs.believed.round_index}, "
        f"${obs.believed.cash}, placed={len(obs.believed.placed)}"
    )

    obs = Executor().run(harness, PLAN)
    vprint(
        f"Done: round {obs.believed.round_index}, "
        f"${obs.believed.cash}, placed={len(obs.believed.placed)}, "
        f"last_ok={obs.sensed.last_step_ok}"
    )
    for tower in obs.believed.placed:
        vprint(f"  {tower.ref}: {tower.tower} @ {tower.position} {tower.upgrades}")


if __name__ == "__main__":
    main()
