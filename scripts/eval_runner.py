#!/usr/bin/env python3
"""
eval_runner.py — 20-run evaluation harness for the Celesto agent sandbox.

Requires:
  - CELESTO_API_KEY environment variable (or set in .env)
  - Celesto SDK installed: pip install celesto

When the SDK is unavailable, prints a clear message and exits with code 1.
"""
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Allow running from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

NUM_RUNS = 20
PROBLEM_ID = "problem-demo"
TASK_COMMAND = (
    "git clone https://github.com/example/repo.git /tmp/repo 2>/dev/null || true && "
    "echo 'task complete' > /tmp/proof.txt && cat /tmp/proof.txt"
)
REPORTS_DIR = PROJECT_ROOT / "reports"
OUTPUT_FILE = REPORTS_DIR / "reliability.json"


def make_sandbox_name(index: int) -> str:
    return f"sbx-eval{index:05d}"


def run_single(index: int) -> dict:
    """Run one agent task in a fresh Celesto sandbox. Returns a result dict."""
    from app.provider import run_in_sandbox, CelestoUnavailableError  # noqa: E402

    sandbox_name = make_sandbox_name(index)
    t_start = time.monotonic()
    result = {
        "sandbox_name": sandbox_name,
        "fresh": True,
        "success": False,
        "wall_clock_s": 0.0,
        "boot_to_ready_s": 0.0,
        "cost_usd": 0.0,
    }

    try:
        outcome = run_in_sandbox(TASK_COMMAND, sandbox_name=sandbox_name)
        result["success"] = outcome["exit_code"] == 0
        result["wall_clock_s"] = outcome["wall_clock_s"]
        result["boot_to_ready_s"] = outcome["boot_to_ready_s"]
        result["cost_usd"] = outcome["cost_usd"]
    except Exception as exc:
        result["error"] = str(exc)
        result["wall_clock_s"] = round(time.monotonic() - t_start, 3)

    return result


def compute_statistics(runs: list) -> dict:
    wall_clocks = sorted(r["wall_clock_s"] for r in runs)
    boots = sorted(r["boot_to_ready_s"] for r in runs)
    n = len(wall_clocks)
    successes = sum(1 for r in runs if r["success"])

    # median: mean of n//2 th and (n//2 + 1)th values (1-indexed)
    mid = n // 2
    median = (wall_clocks[mid - 1] + wall_clocks[mid]) / 2

    # p90: 18th value when n=20
    p90_idx = int(n * 0.9) - 1
    p90 = wall_clocks[p90_idx]

    median_boot = (boots[mid - 1] + boots[mid]) / 2
    total_cost = sum(r["cost_usd"] for r in runs)

    return {
        "total_runs": n,
        "success_count": successes,
        "failure_count": n - successes,
        "success_rate": round(successes / n, 4),
        "wall_clock_s": {
            "sorted": wall_clocks,
            "median": round(median, 4),
            "p90": round(p90, 4),
        },
        "boot_to_ready_s": {
            "sorted": boots,
            "median_boot": round(median_boot, 4),
        },
        "total_cost_usd": round(total_cost, 4),
    }


def main():
    api_key = os.environ.get("CELESTO_API_KEY", "")
    if not api_key or api_key == "replace-me":
        print(
            "ERROR: CELESTO_API_KEY is not set or is a placeholder.\n"
            "Set a real API key in your .env file before running the eval harness.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Verify SDK availability before starting runs
    try:
        try:
            import smolvm  # noqa: F401
        except ImportError:
            import celesto  # noqa: F401
    except ImportError:
        print(
            "ERROR: Celesto SDK is not installed.\n"
            "Install it with: pip install celesto\n"
            "The eval harness cannot proceed without the SDK.",
            file=sys.stderr,
        )
        sys.exit(1)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    runs = []

    print(f"Starting {NUM_RUNS}-run evaluation harness...")
    for i in range(1, NUM_RUNS + 1):
        print(f"  Run {i:2d}/{NUM_RUNS} — {make_sandbox_name(i)} ...", end=" ", flush=True)
        result = run_single(i)
        runs.append(result)
        status = "OK" if result["success"] else "FAIL"
        print(f"{status}  ({result['wall_clock_s']:.1f}s)")

    stats = compute_statistics(runs)
    output = {
        "runs": runs,
        "statistics": stats,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Results from live Celesto SDK runs. "
            "See reports/postmortem.md for context."
        ),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults written to {OUTPUT_FILE}")
    print(f"Success rate : {stats['success_rate']*100:.1f}%")
    print(f"Median wall  : {stats['wall_clock_s']['median']:.2f}s")
    print(f"p90 wall     : {stats['wall_clock_s']['p90']:.2f}s")
    print(f"Total cost   : ${stats['total_cost_usd']:.4f}")


if __name__ == "__main__":
    main()
