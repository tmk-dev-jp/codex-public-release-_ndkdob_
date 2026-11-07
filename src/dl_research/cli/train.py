from __future__ import annotations

from dl_research.cli.common import config_parser, run_cli
from dl_research.experiment.runner import ExperimentRunner


def _execute() -> str:
    args = config_parser("Train one configured experiment.").parse_args()
    result = ExperimentRunner.from_path(args.config).train()
    return f"{result['experiment_id']} train_metrics.json"


def main() -> int:
    return run_cli("train", _execute)


if __name__ == "__main__":
    raise SystemExit(main())
