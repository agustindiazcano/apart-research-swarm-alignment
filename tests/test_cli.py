"""Tests for the command line stub."""
from __future__ import annotations

import pytest

from swarmlab import cli


def test_help_exits_zero_and_lists_name(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        cli.main(["--help"])
    assert info.value.code == 0
    assert "swarmlab" in capsys.readouterr().out


def test_version_prints_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        cli.main(["--version"])
    assert info.value.code == 0
    assert capsys.readouterr().out.strip().startswith("swarmlab ")


def test_unknown_command_exits_with_error() -> None:
    with pytest.raises(SystemExit) as info:
        cli.main(["no-such-command"])
    assert info.value.code != 0
