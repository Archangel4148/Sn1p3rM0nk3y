"""Replay and evaluate the Meadow smoke plan on SimulatedHarness."""

from plans.meadow_smoke import PLAN, SETUP
from planning.evaluate import evaluate_plan
from system_flags import vprint


def main() -> None:
    report = evaluate_plan(SETUP, PLAN)
    if report.illegal_purchase:
        summary = f"Plan ILLEGAL ({report.illegal_purchase})"
    elif report.ok:
        summary = "Plan estimated SURVIVE"
    else:
        summary = "Plan estimated LOSE"
        if report.first_loss_round is not None:
            summary += f" (first loss round {report.first_loss_round})"
    if report.error and not report.illegal_purchase:
        summary += f" error={report.error}"
    vprint(summary)

    for verdict in report.rounds:
        mark = "ok" if not verdict.estimated_lose else "LOSE"
        vprint(
            f"  r{verdict.round_num} [{mark}/{verdict.status.value}] "
            f"rbe={verdict.rbe} dps={verdict.board_dps:.1f} {verdict.detail}"
        )


if __name__ == "__main__":
    main()
