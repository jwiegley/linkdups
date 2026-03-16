"""Tests for linkdups core logic."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from linkdups.core import (
    DuplicateFinder,
    LinkDupsConfig,
    _compute_checksum_python,
    bytestring,
    compute_checksum,
    run,
)


class TestBytestring:
    def test_bytes(self) -> None:
        assert bytestring(0) == "0 bytes"
        assert bytestring(100) == "100 bytes"
        assert bytestring(1023) == "1023 bytes"

    def test_kib(self) -> None:
        assert bytestring(1024) == "1 KiB"
        assert bytestring(2048) == "2 KiB"

    def test_mib(self) -> None:
        assert bytestring(1024 * 1024) == "1.0 MiB"
        assert bytestring(int(1.5 * 1024 * 1024)) == "1.5 MiB"

    def test_gib(self) -> None:
        assert bytestring(1024 * 1024 * 1024) == "1.00 GiB"

    def test_large_gib(self) -> None:
        assert bytestring(10 * 1024 * 1024 * 1024) == "10.00 GiB"


class TestChecksum:
    def test_consistent(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_bytes(b"hello world")
        h1 = _compute_checksum_python(str(f))
        h2 = _compute_checksum_python(str(f))
        assert h1 == h2

    def test_different_content(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"hello")
        f2.write_bytes(b"world")
        assert _compute_checksum_python(str(f1)) != _compute_checksum_python(str(f2))

    def test_compute_checksum_returns_string(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_bytes(b"test content")
        result = compute_checksum(str(f))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_file_checksum(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        h = _compute_checksum_python(str(f))
        assert isinstance(h, str)
        assert len(h) > 0


class TestDuplicateFinder:
    def test_scan_finds_files(self, tmp_tree: Path) -> None:
        config = LinkDupsConfig()
        finder = DuplicateFinder(config)
        finder.config.minimum_size = -1
        finder.config.maximum_size = -1
        finder.scan(str(tmp_tree))
        assert len(finder.files) > 0

    def test_link_duplicates_saves_space(self, tmp_tree: Path) -> None:
        config = LinkDupsConfig()
        finder = DuplicateFinder(config)
        finder.config.minimum_size = -1
        finder.config.maximum_size = -1
        finder.scan(str(tmp_tree))
        bytes_saved = finder.link_duplicates()
        assert bytes_saved > 0

    def test_linked_files_share_inode(self, tmp_tree: Path) -> None:
        config = LinkDupsConfig()
        finder = DuplicateFinder(config)
        finder.config.minimum_size = -1
        finder.config.maximum_size = -1
        finder.scan(str(tmp_tree))
        finder.link_duplicates()

        large_a = tmp_tree / "dir1" / "large_a.dat"
        large_a_copy = tmp_tree / "dir2" / "large_a_copy.dat"
        assert os.stat(str(large_a)).st_ino == os.stat(str(large_a_copy)).st_ino

    def test_dry_run_no_changes(self, tmp_tree: Path) -> None:
        config = LinkDupsConfig(dry_run=True)
        finder = DuplicateFinder(config)
        finder.config.minimum_size = -1
        finder.config.maximum_size = -1
        finder.scan(str(tmp_tree))

        large_a_copy = tmp_tree / "dir2" / "large_a_copy.dat"
        inode_before = os.stat(str(large_a_copy)).st_ino

        finder.link_duplicates()

        inode_after = os.stat(str(large_a_copy)).st_ino
        assert inode_before == inode_after

    def test_empty_directory(self, tmp_path: Path) -> None:
        config = LinkDupsConfig()
        finder = DuplicateFinder(config)
        finder.config.minimum_size = -1
        finder.config.maximum_size = -1
        finder.scan(str(tmp_path))
        bytes_saved = finder.link_duplicates()
        assert bytes_saved == 0

    def test_unique_files_not_linked(self, tmp_path: Path) -> None:
        (tmp_path / "a.dat").write_bytes(b"content one " * 100)
        (tmp_path / "b.dat").write_bytes(b"content two " * 100)

        config = LinkDupsConfig()
        finder = DuplicateFinder(config)
        finder.config.minimum_size = -1
        finder.config.maximum_size = -1
        finder.scan(str(tmp_path))
        bytes_saved = finder.link_duplicates()
        assert bytes_saved == 0

    def test_verbose_output(
        self, tmp_tree: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config = LinkDupsConfig(verbose=True)
        finder = DuplicateFinder(config)
        finder.config.minimum_size = -1
        finder.config.maximum_size = -1
        finder.scan(str(tmp_tree))
        finder.link_duplicates()
        captured = capsys.readouterr()
        assert "Scanning" in captured.err

    def test_size_filtering_minimum(self, tmp_path: Path) -> None:
        (tmp_path / "tiny.dat").write_bytes(b"x" * 10)
        (tmp_path / "tiny_dup.dat").write_bytes(b"x" * 10)

        config = LinkDupsConfig(minimum_size=100)
        finder = DuplicateFinder(config)
        finder.scan(str(tmp_path))
        assert len(finder.files) == 0

    def test_size_filtering_maximum(self, tmp_path: Path) -> None:
        (tmp_path / "big.dat").write_bytes(b"x" * 10000)
        (tmp_path / "big_dup.dat").write_bytes(b"x" * 10000)

        config = LinkDupsConfig(maximum_size=100)
        finder = DuplicateFinder(config)
        finder.scan(str(tmp_path))
        assert len(finder.files) == 0

    def test_skips_zero_size_files(self, tmp_path: Path) -> None:
        (tmp_path / "empty1.dat").write_bytes(b"")
        (tmp_path / "empty2.dat").write_bytes(b"")

        config = LinkDupsConfig()
        finder = DuplicateFinder(config)
        finder.config.minimum_size = -1
        finder.config.maximum_size = -1
        finder.scan(str(tmp_path))
        assert len(finder.files) == 0


class TestRun:
    def test_run_with_directory(
        self,
        tmp_tree: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        bytes_saved = run([str(tmp_tree)])
        assert bytes_saved > 0
        captured = capsys.readouterr()
        assert "Saved" in captured.out

    def test_run_with_nonexistent(self, capsys: pytest.CaptureFixture[str]) -> None:
        run(["/nonexistent/path/that/does/not/exist"])
        captured = capsys.readouterr()
        assert "not a directory" in captured.err

    def test_run_dry_run(
        self,
        tmp_tree: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        bytes_saved = run([str(tmp_tree)], dry_run=True)
        captured = capsys.readouterr()
        assert "Saved" in captured.out
        assert "os.remove" in captured.out or bytes_saved == 0

    def test_run_verbose(
        self,
        tmp_tree: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        run([str(tmp_tree)], verbose=True)
        captured = capsys.readouterr()
        assert "Scanning" in captured.err
