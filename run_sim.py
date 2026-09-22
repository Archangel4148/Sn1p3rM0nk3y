"""Replay and evaluate the Meadow smoke plan on SimulatedHarness."""

from plans.meadow_smoke import PLAN, SETUP
from planning.evaluate import evaluate_plan
from system_flags import vprint


def main() -> None:
    report = evaluate_plan(SETUP, PLAN)
    vprint(
        f"Plan estimated {'SURVIVE' if report.ok else 'LOSE'}"
        + (f" (first loss round {report.first_loss_round})" if report.first_loss_round else "")
        + (f" error={report.error}" if report.error else "")
    )
    for verdict in report.rounds:
        mark = "ok" if not verdict.estimated_lose else "LOSE"
        vprint(
            f"  r{verdict.round_num} [{mark}/{verdict.status.value}] "
            f"rbe={verdict.rbe} dps={verdict.board_dps:.1f} {verdict.detail}"
        )


if __name__ == "__main__":
    main()
