"""Command-line interface for linkdups."""

from __future__ import annotations

import argparse

from . import __version__
from .core import run


def main(argv: list[str] | None = None) -> None:
    """Main entry point for the linkdups CLI."""
    parser = argparse.ArgumentParser(
        prog="linkdups",
        description="Find and hard-link duplicate files to save disk space.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="report activity verbosely",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        default=False,
        help="make no changes to disk",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="directories to scan (default: current directory)",
    )

    args = parser.parse_args(argv)
    run(args.paths, verbose=args.verbose, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
