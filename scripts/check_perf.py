#!/usr/bin/env python3
"""Compare benchmark results against a saved baseline.

Usage: check_perf.py <results.json>

Fails if any benchmark regresses by more than 10% compared to baseline.
If no baseline exists, prints a warning and exits successfully.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASELINE_PATH = Path(".benchmarks/baseline.json")
MAX_REGRESSION_PCT = 10.0


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: check_perf.py <results.json>", file=sys.stderr)
        return 1

    results_path = Path(sys.argv[1])

    if not BASELINE_PATH.exists():
        print(
            "No baseline found. Run:\n"
            "  PYTHONPATH=src pytest tests/test_benchmark.py "
            "--benchmark-json=.benchmarks/baseline.json",
            file=sys.stderr,
        )
        return 0

    with open(BASELINE_PATH) as f:
        baseline = json.load(f)
    with open(results_path) as f:
        results = json.load(f)

    baseline_medians: dict[str, float] = {
        b["name"]: b["stats"]["median"] for b in baseline["benchmarks"]
    }
    results_medians: dict[str, float] = {
        b["name"]: b["stats"]["median"] for b in results["benchmarks"]
    }

    failed = False
    for name, result_median in results_medians.items():
        if name in baseline_medians:
            baseline_median = baseline_medians[name]
            if baseline_median > 0:
                regression = (result_median - baseline_median) / baseline_median * 100
            else:
                regression = 0.0

            if regression > MAX_REGRESSION_PCT:
                print(
                    f"FAIL: {name} regressed by {regression:.1f}% "
                    f"(baseline: {baseline_median:.6f}s, "
                    f"current: {result_median:.6f}s)"
                )
                failed = True
            else:
                print(f"OK: {name} ({regression:+.1f}%)")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
