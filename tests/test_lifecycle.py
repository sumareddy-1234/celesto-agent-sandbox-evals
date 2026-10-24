"""
tests/test_lifecycle.py — Tests for sandbox naming, cleanup flags, and failure-trace integrity.

Label: OFFLINE — validates report schemas and business-logic constraints.
No live Celesto runs or database connection required.
"""
import json
import re
import sys
from pathlib import Path
from math import ceil

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = Path(__file__).resolve().parent.parent
SANDBOX_RE = re.compile(r"^sbx-[a-z0-9]{8,}$")


# ─────────────────────────────────────────────
# Sandbox name generator
# ─────────────────────────────────────────────

class TestSandboxNameGenerator:
    def test_generated_names_match_pattern(self):
        from app.provider import _make_sandbox_name
        for _ in range(50):
            name = _make_sandbox_name()
            assert SANDBOX_RE.match(name), f"Generated name {name!r} does not match pattern"

    def test_generated_names_are_unique(self):
        from app.provider import _make_sandbox_name
        names = [_make_sandbox_name() for _ in range(100)]
        assert len(set(names)) == 100, "Generated sandbox names are not unique"


# ─────────────────────────────────────────────
# Lifecycle report
# ─────────────────────────────────────────────

class TestLifecycleReport:
    @pytest.fixture(autouse=True)
    def load(self):
        path = BASE / "reports" / "lifecycle.json"
        self.data = json.loads(path.read_text())

    def test_cleanup_on_success(self):
        assert self.data["cleanup_on_success"] is True

    def test_cleanup_on_failure(self):
        assert self.data["cleanup_on_failure"] is True

    def test_cleanup_on_interrupt(self):
        assert self.data["cleanup_on_interrupt"] is True

    def test_sandbox_names_are_valid(self):
        for name in self.data["sandbox_names"]:
            assert SANDBOX_RE.match(name), f"Invalid sandbox name in lifecycle.json: {name!r}"

    def test_sandbox_names_are_unique(self):
        names = self.data["sandbox_names"]
        assert len(set(names)) == len(names), "Duplicate sandbox names in lifecycle.json"

    def test_sandbox_names_appear_in_command_log_or_reliability(self):
        # At least one name from lifecycle.json must appear in commands.jsonl or reliability.json
        cmd_path = BASE / "logs" / "commands.jsonl"
        rel_path = BASE / "reports" / "reliability.json"
        cmd_text = cmd_path.read_text() if cmd_path.exists() else ""
        rel_text = rel_path.read_text() if rel_path.exists() else ""
        combined = cmd_text + rel_text
        found = any(name in combined for name in self.data["sandbox_names"])
        assert found, "No lifecycle sandbox_names appear in commands.jsonl or reliability.json"


# ─────────────────────────────────────────────
# Failure trace integrity
# ─────────────────────────────────────────────

class TestFailureTrace:
    @pytest.fixture(autouse=True)
    def load(self):
        path = BASE / "reports" / "failure_trace.jsonl"
        self.events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    def test_trace_has_events(self):
        assert len(self.events) > 0

    def test_all_events_have_ts_and_event(self):
        for ev in self.events:
            assert "ts" in ev, f"Missing ts in event: {ev}"
            assert "event" in ev, f"Missing event in event: {ev}"

    def test_step_7_fail_event_exists(self):
        step7_fails = [e for e in self.events if e.get("event") == "step_failed" and e.get("step") == 7]
        assert step7_fails, "No step_failed event for step 7 found in failure_trace.jsonl"

    def test_policy_applied_event_exists(self):
        policy_events = [e for e in self.events if e.get("event") == "policy_applied"]
        assert policy_events, "No policy_applied event found in failure_trace.jsonl"

    def test_policy_applied_matches_failure_policy(self):
        fp = json.loads((BASE / "reports" / "failure_policy.json").read_text())
        policy_events = [e for e in self.events if e.get("event") == "policy_applied"]
        assert any(e.get("policy") == fp["policy"] for e in policy_events), (
            f"policy_applied event does not match failure_policy.json policy={fp['policy']!r}"
        )

    def test_sandbox_deleted_event_exists(self):
        delete_events = [e for e in self.events if e.get("event") == "sandbox_deleted"]
        assert delete_events, "No sandbox_deleted event found — lifecycle hygiene requires cleanup"


# ─────────────────────────────────────────────
# Reliability statistics correctness
# ─────────────────────────────────────────────

class TestReliabilityStatistics:
    @pytest.fixture(autouse=True)
    def load(self):
        path = BASE / "reports" / "reliability.json"
        self.data = json.loads(path.read_text())
        self.runs = self.data["runs"]
        self.n = len(self.runs)

    def test_run_count_matches_runs_length(self):
        assert self.data["run_count"] == self.n

    def test_success_rate_computed_correctly(self):
        expected = sum(1 for r in self.runs if r["success"]) / self.n
        assert abs(self.data["success_rate"] - expected) < 0.001

    def test_median_wall_clock_correct(self):
        sorted_wc = sorted(r["wall_clock_s"] for r in self.runs)
        n = len(sorted_wc)
        mid = n // 2
        expected = (sorted_wc[mid - 1] + sorted_wc[mid]) / 2
        assert abs(self.data["median_wall_clock_s"] - expected) < 0.001

    def test_p90_wall_clock_correct(self):
        sorted_wc = sorted(r["wall_clock_s"] for r in self.runs)
        n = len(sorted_wc)
        p90_idx = ceil(0.90 * n) - 1
        expected = sorted_wc[p90_idx]
        assert abs(self.data["p90_wall_clock_s"] - expected) < 0.001

    def test_median_boot_correct(self):
        sorted_boot = sorted(r["boot_to_ready_s"] for r in self.runs)
        n = len(sorted_boot)
        mid = n // 2
        expected = (sorted_boot[mid - 1] + sorted_boot[mid]) / 2
        assert abs(self.data["median_boot_to_ready_s"] - expected) < 0.001

    def test_total_cost_correct(self):
        expected = sum(r["cost_usd"] for r in self.runs)
        assert abs(self.data["total_cost_usd"] - expected) < 0.01

    def test_postmortem_path_exists(self):
        pm_path = BASE / self.data["postmortem_path"]
        assert pm_path.exists(), f"postmortem_path {pm_path} does not exist"

    def test_postmortem_has_enough_content(self):
        pm_path = BASE / self.data["postmortem_path"]
        assert len(pm_path.read_text()) >= 200, "postmortem.md is shorter than 200 characters"
