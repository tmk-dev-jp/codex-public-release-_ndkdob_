__all__ = ["ExperimentRunner"]


def __getattr__(name: str):
    if name == "ExperimentRunner":
        from dl_research.experiment.runner import ExperimentRunner

        return ExperimentRunner
    raise AttributeError(name)
