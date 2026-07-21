"""Application-specific exceptions."""

from collections.abc import Sequence


class ConfigLoadError(ValueError):
    """Raised when a configuration file cannot be loaded or parsed."""


class ConfigValidationError(ValueError):
    """Raised when an experiment configuration is invalid."""

    def __init__(self, errors: Sequence[str]) -> None:
        """Create an exception containing all detected validation errors."""
        self.errors = tuple(errors)

        message = "Invalid experiment configuration:\n" + "\n".join(
            f"- {error}" for error in self.errors
        )

        super().__init__(message)


class DataValidationError(ValueError):
    """Raised when scenario input data is invalid."""