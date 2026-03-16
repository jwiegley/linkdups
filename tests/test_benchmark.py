"""Performance benchmarks for linkdups."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from linkdups.core import (
    DuplicateFinder,
    LinkDupsConfig,
    _compute_checksum_python,
    bytestring,
)


@pytest.fixture()
def large_tree(tmp_path: Path) -> Path:
    """Create a directory with many files for benchmarking."""
    content = b"benchmark content " * 500
    for i in range(100):
        (tmp_path / f"file_{i:03d}.dat").write_bytes(content)
    dup_content = b"duplicate " * 1000
    for i in range(20):
        (tmp_path / f"dup_{i:03d}.dat").write_bytes(dup_content)
    return tmp_path


def test_benchmark_checksum(benchmark: Any, tmp_path: Path) -> None:
    f = tmp_path / "bench.dat"
    f.write_bytes(b"x" * 100000)
    benchmark(_compute_checksum_python, str(f))


def test_benchmark_scan(benchmark: Any, large_tree: Path) -> None:
    def do_scan() -> None:
        config = LinkDupsConfig()
        finder = DuplicateFinder(config)
        finder.config.minimum_size = -1
        finder.config.maximum_size = -1
        finder.scan(str(large_tree))

    benchmark(do_scan)


def test_benchmark_bytestring(benchmark: Any) -> None:
    benchmark(bytestring, 1234567890)
