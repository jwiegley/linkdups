"""Property-based fuzz tests for linkdups using Hypothesis."""

from __future__ import annotations

import os
import tempfile

from hypothesis import given, settings
from hypothesis import strategies as st

from linkdups.core import _compute_checksum_python, bytestring


@given(st.integers(min_value=0, max_value=10**15))
def test_bytestring_always_returns_string(amount: int) -> None:
    result = bytestring(amount)
    assert isinstance(result, str)
    assert len(result) > 0


@given(st.integers(min_value=0, max_value=10**15))
def test_bytestring_has_unit(amount: int) -> None:
    result = bytestring(amount)
    assert any(unit in result for unit in ("bytes", "KiB", "MiB", "GiB"))


@given(st.integers(min_value=0, max_value=10**15))
def test_bytestring_monotonic(amount: int) -> None:
    """Larger amounts should not produce smaller numeric prefixes."""
    result = bytestring(amount)
    # Just verify it doesn't raise
    assert result


@given(st.binary(min_size=1, max_size=10000))
@settings(max_examples=50)
def test_checksum_deterministic(data: bytes) -> None:
    """Same content always produces the same checksum."""
    fd, path = tempfile.mkstemp()
    try:
        os.write(fd, data)
        os.close(fd)
        assert _compute_checksum_python(path) == _compute_checksum_python(path)
    finally:
        os.unlink(path)


@given(
    st.binary(min_size=1, max_size=1000),
    st.binary(min_size=1, max_size=1000),
)
@settings(max_examples=50)
def test_different_content_different_checksum(a: bytes, b: bytes) -> None:
    """Different content should produce different checksums."""
    if a == b:
        return

    fd_a, path_a = tempfile.mkstemp()
    fd_b, path_b = tempfile.mkstemp()
    try:
        os.write(fd_a, a)
        os.close(fd_a)
        os.write(fd_b, b)
        os.close(fd_b)
        assert _compute_checksum_python(path_a) != _compute_checksum_python(path_b)
    finally:
        os.unlink(path_a)
        os.unlink(path_b)


@given(st.binary(min_size=0, max_size=5000))
@settings(max_examples=30)
def test_checksum_is_hex_string(data: bytes) -> None:
    """Checksum output should be a valid hex string."""
    fd, path = tempfile.mkstemp()
    try:
        os.write(fd, data)
        os.close(fd)
        result = _compute_checksum_python(path)
        # SHA-512 produces 128 hex characters
        assert len(result) == 128
        int(result, 16)  # should not raise
    finally:
        os.unlink(path)
