from __future__ import annotations

from dl_research.cli.common import config_parser, run_cli
from dl_research.experiment.runner import ExperimentRunner


def _execute() -> str:
    args = config_parser("Run training and test evaluation once.").parse_args()
    result = ExperimentRunner.from_path(args.config).cycle()
    metric = result["primary_metric"]
    return f"{result['experiment_id']} {metric['name']}={metric['value']:.6f}"


def main() -> int:
    return run_cli("cycle", _execute)


if __name__ == "__main__":
    raise SystemExit(main())
