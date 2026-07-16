"""Smoke tests for the initial package skeleton."""

import pytest

from ci_experiment_analyzer import __version__
from ci_experiment_analyzer.cli import main


def test_package_has_version() -> None:
    """The package should expose its current version."""
    assert __version__ == "0.1.0"


def test_cli_displays_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should display its version and exit successfully."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    assert exc_info.value.code == 0
    assert "ci-analyzer 0.1.0" in capsys.readouterr().out