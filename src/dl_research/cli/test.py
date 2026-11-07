from __future__ import annotations

from dl_research.cli.common import config_parser, run_cli
from dl_research.experiment.runner import ExperimentRunner


def _execute() -> str:
    args = config_parser("Evaluate one configured checkpoint.").parse_args()
    result = ExperimentRunner.from_path(args.config).test()
    return f"{result['experiment_id']} test_metrics.json"


def main() -> int:
    return run_cli("test", _execute)


if __name__ == "__main__":
    raise SystemExit(main())
