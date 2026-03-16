"""Shared test fixtures for linkdups tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def tmp_tree(tmp_path: Path) -> Path:
    """Create a temporary directory tree with duplicate files."""
    content_large = b"duplicate large content " * 2000  # ~46 KiB
    content_small = b"small dup " * 100  # ~1 KiB
    content_unique = b"this content is unique and not duplicated anywhere"

    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()

    # Duplicate large files
    (dir1 / "large_a.dat").write_bytes(content_large)
    (dir2 / "large_a_copy.dat").write_bytes(content_large)

    # Duplicate small files
    (dir1 / "small_a.txt").write_bytes(content_small)
    (dir2 / "small_a_copy.txt").write_bytes(content_small)

    # Unique file
    (dir1 / "unique.dat").write_bytes(content_unique)

    return tmp_path
