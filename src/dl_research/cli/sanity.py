from __future__ import annotations

from dl_research.cli.common import config_parser, run_cli
from dl_research.experiment.runner import ExperimentRunner


def _execute() -> str:
    args = config_parser("Run one forward and backward contract check.").parse_args()
    result = ExperimentRunner.from_path(args.config).sanity()
    return (
        f"{result['experiment_id']} loss={result['loss']:.6f} "
        f"output_shape={result['output_shape']}"
    )


def main() -> int:
    return run_cli("sanity", _execute)


if __name__ == "__main__":
    raise SystemExit(main())
