"""Core logic for finding and linking duplicate files."""

from __future__ import annotations

import filecmp
import hashlib
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from stat import S_ISDIR, S_ISREG, ST_MODE, ST_NLINK, ST_SIZE

# Directories to skip during traversal
_SKIP_DIRS = frozenset(("/proc", "/dev", "/sys", "/mnt"))

# File extensions to skip
_SKIP_EXTENSIONS = (".dtBase2", ".sparsebundle")


@dataclass
class LinkDupsConfig:
    """Configuration for duplicate file linking."""

    verbose: bool = False
    dry_run: bool = False
    minimum_size: int = -1
    maximum_size: int = -1


def bytestring(amount: int) -> str:
    """Format a byte count as a human-readable string."""
    if amount < 1024:
        return f"{amount} bytes"
    elif amount < 1024 * 1024:
        return f"{amount // 1024} KiB"
    elif amount < 1024 * 1024 * 1024:
        return f"{amount / (1024.0 * 1024.0):.1f} MiB"
    else:
        return f"{amount / (1024.0 * 1024.0 * 1024.0):.2f} GiB"


def compute_checksum(path: str) -> str:
    """Compute file checksum, using b3sum if available, else SHA-512."""
    if shutil.which("b3sum"):
        try:
            result = subprocess.run(
                ["b3sum", path],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.split()[0]
        except (subprocess.SubprocessError, IndexError):
            pass
    return _compute_checksum_python(path)


def _compute_checksum_python(path: str) -> str:
    """Compute SHA-512 checksum using pure Python."""
    csum = hashlib.sha512()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            csum.update(chunk)
    return csum.hexdigest()


class DuplicateFinder:
    """Finds and links duplicate files in directory trees."""

    def __init__(self, config: LinkDupsConfig) -> None:
        self.config = config
        self.files: dict[int, list[str]] = {}
        self.counter = 0
        self.bytes_saved = 0

    def scan(self, path: str) -> None:
        """Scan a directory tree for files, grouped by size."""
        self._find_matches(path, 0)

    def _find_matches(self, path: str, depth: int) -> None:
        """Recursively walk directory tree, recording files by size."""
        try:
            entries = os.listdir(path)
        except PermissionError:
            return

        if depth <= 1 and self.config.verbose:
            print(f".. Scanning for entries in {path}", file=sys.stderr)

        for entry_name in entries:
            if any(entry_name.endswith(ext) for ext in _SKIP_EXTENSIONS):
                continue

            self.counter += 1
            if self.counter % 10000 == 0 and self.config.verbose:
                print(f".. Scanned {self.counter} entries", file=sys.stderr)

            entry = os.path.join(path, entry_name)
            try:
                mode = os.lstat(entry)[ST_MODE]
            except OSError:
                continue

            if S_ISDIR(mode) and entry not in _SKIP_DIRS:
                self._find_matches(entry, depth + 1)
            elif S_ISREG(mode):
                self._record_size_match(entry)

    def _record_size_match(self, path: str) -> None:
        """Record a file by its size for later comparison."""
        try:
            size = os.lstat(path)[ST_SIZE]
        except OSError:
            return

        if size == 0:
            return
        if self.config.minimum_size > 0 and size < self.config.minimum_size:
            return
        if self.config.maximum_size > 0 and size >= self.config.maximum_size:
            return

        if size not in self.files:
            self.files[size] = [path]
        else:
            self.files[size].append(path)

    def link_duplicates(self) -> int:
        """Link duplicate files and return total bytes saved."""
        keys = sorted(self.files.keys(), reverse=True)

        for size in keys:
            paths = self.files[size]
            if len(paths) < 2:
                continue

            if self.config.verbose:
                print(
                    f".. Scanning {len(paths)} files of size {size} "
                    "for checksum matches",
                    file=sys.stderr,
                )

            checksum_groups: dict[str, list[str]] = {}
            for path in paths:
                try:
                    digest = compute_checksum(path)
                except OSError:
                    continue
                if digest not in checksum_groups:
                    checksum_groups[digest] = [path]
                else:
                    checksum_groups[digest].append(path)

            for _digest, group in checksum_groups.items():
                if len(group) < 2:
                    continue

                if self.config.verbose:
                    print(
                        f" --> Found a group of {len(group)} files of "
                        f"size {size}, based on checksum",
                        file=sys.stderr,
                    )

                self._link_group(group, size)

        return self.bytes_saved

    def _link_group(self, group: list[str], size: int) -> None:
        """Hard-link a group of identical files together."""
        referent = None
        unmatched = 0

        for path in group:
            try:
                info = os.lstat(path)
            except OSError:
                continue
            if info[ST_NLINK] > 1:
                referent = path
            else:
                unmatched += 1

        if not unmatched:
            return

        if self.config.verbose:
            print(
                f"   ==> of these, {unmatched} of the matching files are unpaired",
                file=sys.stderr,
            )

        if not referent:
            referent = group[0]

        first = True
        for path in group:
            if path is referent:
                continue

            if not filecmp.cmp(path, referent):
                continue

            try:
                if self.config.dry_run:
                    print(f'os.remove("{path}")')
                else:
                    os.remove(path)
            finally:
                # Ensure the link is created even if Control-C hits
                # between remove and link
                if self.config.dry_run:
                    print(f"os.link({referent}, {path})")
                elif not os.path.exists(path):
                    os.link(referent, path)

            self.bytes_saved += size
            if self.config.verbose:
                if first:
                    print(f"    {referent} ->", file=sys.stderr)
                    first = False
                print(f"       {path}", file=sys.stderr)


def run(
    paths: list[str],
    *,
    verbose: bool = False,
    dry_run: bool = False,
) -> int:
    """Run the duplicate linking process on the given paths.

    Returns the total bytes saved.
    """
    finder = DuplicateFinder(LinkDupsConfig(verbose=verbose, dry_run=dry_run))

    for path in paths:
        if os.path.isfile(path):
            finder._record_size_match(path)
        elif not os.path.isdir(path):
            print(f"{path} is not a directory!", file=sys.stderr)
        else:
            # First pass: large files (>= 16 KiB)
            if verbose:
                print(f".. Scanning for large files in {path}", file=sys.stderr)
            finder.config.maximum_size = -1
            finder.config.minimum_size = 16 * 1024
            finder.scan(path)
            if verbose:
                print(
                    f":: Scanned {len(finder.files)} size groups",
                    file=sys.stderr,
                )

            # Second pass: small files (< 16 KiB)
            if verbose:
                print(f".. Scanning for small files in {path}", file=sys.stderr)
            finder.config.maximum_size = 16 * 1024
            finder.config.minimum_size = -1
            finder.scan(path)
            if verbose:
                print(
                    f":: Scanned {len(finder.files)} size groups",
                    file=sys.stderr,
                )

    try:
        bytes_saved = finder.link_duplicates()
    except KeyboardInterrupt:
        bytes_saved = finder.bytes_saved
    finally:
        print(f"Saved {bytestring(finder.bytes_saved)}")

    return bytes_saved
