# linkdups

I've had this script kicking around since 2011. The problem it solves is one
that most programmers end up writing something for at some point -- my brother
was telling me about one he'd written, too. You've got a directory tree full
of duplicate files (backup drives, website mirrors, Time Machine archives),
and you want to reclaim the wasted space by hard-linking identical files
together.

The thing is, I needed it to work at scale. I tested it against a directory
hierarchy containing over 40 million entries. My requirements were that memory
consumption never grew beyond a small startup footprint, and that it not waste
cycles checksumming files that couldn't possibly match.

## How it works

The algorithm is straightforward but has a few tricks:

1. Files are first grouped by size. If only one file has a given size, there's
   no point checksumming it.
2. Large files (>= 16 KiB) are processed first, so you see the biggest
   savings up front. This also keeps internal tables smaller.
3. Within each size group, checksums identify likely matches. It'll use
   `b3sum` if it's on your PATH (quite a bit faster), otherwise falls back to
   SHA-512.
4. Candidates are then byte-wise compared to catch the rare hash collision
   before any linking happens.
5. The duplicate is removed and hard-linked to the original. If you hit
   Control-C at any point, the script wraps up the last task cleanly -- your
   files won't be left in a bad state.

## Installation

Build with Nix:

```
nix build
```

Or install into your profile:

```
nix profile install .
```

For development:

```
nix develop
```

## Usage

```
linkdups [--verbose] [--dry-run] [DIRS...]
```

If no directories are given, it scans the current directory. `--dry-run` shows
what would happen without touching anything. `--verbose` shows the algorithm
at work -- handy if you're curious or impatient.

## Development

Enter the dev shell and run tests:

```
nix develop
pytest tests/ -x -q
```

Run the full suite of checks (formatting, linting, types, tests):

```
nix flake check
```

Save a performance baseline (do this once, then the pre-commit hook will
catch regressions > 5%):

```
PYTHONPATH=src pytest tests/test_benchmark.py --benchmark-json=.benchmarks/baseline.json
```

## License

BSD 3-Clause. See [LICENSE.md](LICENSE.md).
