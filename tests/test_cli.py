"""Tests for the linkdups CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from linkdups.cli import main


class TestCLI:
    def test_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit, match="0"):
            main(["--version"])
        captured = capsys.readouterr()
        assert "linkdups" in captured.out

    def test_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit, match="0"):
            main(["--help"])
        captured = capsys.readouterr()
        assert "duplicate" in captured.out.lower()

    def test_dry_run(
        self,
        tmp_tree: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        main(["--dry-run", str(tmp_tree)])
        captured = capsys.readouterr()
        assert "Saved" in captured.out

    def test_verbose(
        self,
        tmp_tree: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        main(["--verbose", str(tmp_tree)])
        captured = capsys.readouterr()
        assert "Scanning" in captured.err

    def test_default_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.chdir(tmp_path)
        main([])
        captured = capsys.readouterr()
        assert "Saved" in captured.out
