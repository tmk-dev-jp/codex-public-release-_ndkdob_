"""Small exception surface for configuration and execution policy failures."""


class ConfigError(ValueError):
    """Experiment configuration violates a required contract."""


class PolicyError(RuntimeError):
    """Execution exceeds a declared budget or approval boundary."""
