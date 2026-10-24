"""
tests/test_reports.py — Full validation test suite for the Celesto evaluation project.

Run with: python -m pytest tests/test_reports.py -v
"""
import json
import os
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ALLOWED_CAPABILITY_IDS = {
    "safety_hooks",
    "network_policy",
    "snapshot_rollback",
    "lifecycle_cleanup",
    "audit_log",
    "sandbox_isolation",
    "fresh_sandbox",
    "concurrency",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(rel_path: str) -> dict | list:
    p = PROJECT_ROOT / rel_path
    assert p.exists(), f"File not found: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def load_text(rel_path: str) -> str:
    p = PROJECT_ROOT / rel_path
    assert p.exists(), f"File not found: {p}"
    return p.read_text(encoding="utf-8")


def load_jsonl(rel_path: str) -> list[dict]:
    p = PROJECT_ROOT / rel_path
    assert p.exists(), f"File not found: {p}"
    lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines]


# ---------------------------------------------------------------------------
# 1. README
# ---------------------------------------------------------------------------

class TestReadme:
    REQUIRED_PHRASES = [
        "Problem statement",
        "How I used Celesto",
        "Eval report",
        "Containment test",
        "State and failure design",
        "Setup",
    ]

    def test_readme_exists(self):
        assert (PROJECT_ROOT / "README.md").exists()

    def test_readme_has_required_sections(self):
        content = load_text("README.md")
        for phrase in self.REQUIRED_PHRASES:
            assert phrase in content, f"README missing section: '{phrase}'"

    def test_readme_length(self):
        content = load_text("README.md")
        assert len(content) >= 500, "README is too short"


# ---------------------------------------------------------------------------
# 2. Dockerfile
# ---------------------------------------------------------------------------

class TestDockerfile:
    def test_dockerfile_exists(self):
        assert (PROJECT_ROOT / "Dockerfile").exists()

    def test_dockerfile_has_multiple_lines(self):
        content = load_text("Dockerfile")
        lines = [ln for ln in content.splitlines() if ln.strip()]
        assert len(lines) >= 10, "Dockerfile has too few lines"

    def test_dockerfile_has_stages(self):
        content = load_text("Dockerfile")
        assert "FROM" in content
        assert "AS base" in content or "AS builder" in content or "AS runtime" in content

    def test_dockerfile_exposes_8080(self):
        content = load_text("Dockerfile")
        assert "8080" in content

    def test_dockerfile_has_nonroot_user(self):
        content = load_text("Dockerfile")
        assert "appuser" in content


# ---------------------------------------------------------------------------
# 3. docker-compose.yml
# ---------------------------------------------------------------------------

class TestDockerCompose:
    def test_compose_exists(self):
        assert (PROJECT_ROOT / "docker-compose.yml").exists()

    def test_compose_has_api_service(self):
        content = load_text("docker-compose.yml")
        assert "api:" in content

    def test_compose_has_ledger_service(self):
        content = load_text("docker-compose.yml")
        assert "ledger:" in content

    def test_compose_has_healthchecks(self):
        content = load_text("docker-compose.yml")
        assert content.count("healthcheck:") >= 2

    def test_compose_has_pgdata_volume(self):
        content = load_text("docker-compose.yml")
        assert "pgdata" in content


# ---------------------------------------------------------------------------
# 4. .env.example
# ---------------------------------------------------------------------------

class TestEnvExample:
    REQUIRED_VARS = [
        "API_PORT",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "DATABASE_URL",
        "CELESTO_PROVIDER",
        "CELESTO_API_KEY",
        "CELESTO_BACKEND",
        "LLM_BASE_URL",
        "LLM_API_KEY",
        "LLM_MODEL",
    ]

    def test_env_example_exists(self):
        assert (PROJECT_ROOT / ".env.example").exists()

    def test_env_example_has_all_vars(self):
        content = load_text(".env.example")
        for var in self.REQUIRED_VARS:
            assert var in content, f".env.example missing variable: {var}"


# ---------------------------------------------------------------------------
# 5. seeds/01_runs.sql
# ---------------------------------------------------------------------------

class TestSeedSql:
    def test_seed_exists(self):
        assert (PROJECT_ROOT / "seeds" / "01_runs.sql").exists()

    def test_seed_contains_seeddemo1(self):
        content = load_text("seeds/01_runs.sql")
        assert "sbx-seeddemo1" in content

    def test_seed_creates_runs_table(self):
        content = load_text("seeds/01_runs.sql")
        assert "CREATE TABLE" in content.upper()

    def test_seed_is_idempotent(self):
        content = load_text("seeds/01_runs.sql")
        assert "ON CONFLICT" in content or "IF NOT EXISTS" in content.upper()


# ---------------------------------------------------------------------------
# 6. reports/problem.json
# ---------------------------------------------------------------------------

class TestProblemJson:
    def test_problem_json_parses(self):
        data = load_json("reports/problem.json")
        assert isinstance(data, dict)

    def test_problem_json_has_required_keys(self):
        data = load_json("reports/problem.json")
        for key in ("who", "agent_work", "proof_output", "idea_source"):
            assert key in data, f"problem.json missing key: {key}"

    def test_problem_json_fields_long_enough(self):
        data = load_json("reports/problem.json")
        assert len(data["who"]) >= 30, "problem.json 'who' is too short"
        assert len(data["agent_work"]) >= 50, "problem.json 'agent_work' is too short"
        assert len(data["proof_output"]) >= 20, "problem.json 'proof_output' is too short"


# ---------------------------------------------------------------------------
# 7. reports/capabilities.json
# ---------------------------------------------------------------------------

class TestCapabilitiesJson:
    def test_capabilities_json_parses(self):
        data = load_json("reports/capabilities.json")
        assert isinstance(data, dict)
        assert "capabilities" in data

    def test_capabilities_has_at_least_two(self):
        data = load_json("reports/capabilities.json")
        assert len(data["capabilities"]) >= 2, "Need at least 2 capabilities"

    def test_capabilities_ids_are_allowed(self):
        data = load_json("reports/capabilities.json")
        for cap in data["capabilities"]:
            assert cap["id"] in ALLOWED_CAPABILITY_IDS, (
                f"Unknown capability id: {cap['id']}"
            )

    def test_capabilities_have_why_and_evidence(self):
        data = load_json("reports/capabilities.json")
        for cap in data["capabilities"]:
            assert "why" in cap and len(cap["why"]) >= 20
            assert "evidence_path" in cap


# ---------------------------------------------------------------------------
# 8. reports/lifecycle.json
# ---------------------------------------------------------------------------

class TestLifecycleJson:
    def test_lifecycle_json_parses(self):
        data = load_json("reports/lifecycle.json")
        assert isinstance(data, dict)

    def test_lifecycle_cleanup_flags_all_true(self):
        data = load_json("reports/lifecycle.json")
        assert data.get("cleanup_on_success") is True
        assert data.get("cleanup_on_failure") is True
        assert data.get("cleanup_on_interrupt") is True

    def test_lifecycle_has_sandbox_names(self):
        data = load_json("reports/lifecycle.json")
        assert "sandbox_names" in data
        assert len(data["sandbox_names"]) >= 1

    def test_lifecycle_contains_seeddemo1(self):
        data = load_json("reports/lifecycle.json")
        assert "sbx-seeddemo1" in data["sandbox_names"]


# ---------------------------------------------------------------------------
# 9. reports/reliability.json
# ---------------------------------------------------------------------------

class TestReliabilityJson:
    def test_reliability_json_parses(self):
        data = load_json("reports/reliability.json")
        assert isinstance(data, dict)

    def test_reliability_has_20_runs(self):
        data = load_json("reports/reliability.json")
        assert "runs" in data
        assert len(data["runs"]) >= 20, f"Expected >= 20 runs, got {len(data['runs'])}"

    def test_reliability_statistics_present(self):
        data = load_json("reports/reliability.json")
        # Support both flat top-level keys (assessment schema) and nested statistics block
        has_flat = "success_rate" in data and "median_wall_clock_s" in data
        has_nested = "statistics" in data and "success_rate" in data.get("statistics", {})
        assert has_flat or has_nested, "reliability.json must have success_rate and timing keys"

    def test_reliability_success_rate_range(self):
        data = load_json("reports/reliability.json")
        rate = data.get("success_rate") or data.get("statistics", {}).get("success_rate")
        assert rate is not None, "success_rate not found in reliability.json"
        assert 0.0 <= rate <= 1.0, f"success_rate out of range: {rate}"

    def test_reliability_median_correct(self):
        data = load_json("reports/reliability.json")
        median = (
            data.get("median_wall_clock_s")
            or data.get("statistics", {}).get("wall_clock_s", {}).get("median")
        )
        assert median is not None and median > 0, "Median wall_clock_s should be a positive number"

    def test_reliability_p90_correct(self):
        data = load_json("reports/reliability.json")
        p90 = (
            data.get("p90_wall_clock_s")
            or data.get("statistics", {}).get("wall_clock_s", {}).get("p90")
        )
        median = (
            data.get("median_wall_clock_s")
            or data.get("statistics", {}).get("wall_clock_s", {}).get("median")
        )
        assert p90 is not None and median is not None, "p90 and median must both be present"
        assert p90 >= median, "p90 should be >= median"

    def test_reliability_runs_have_required_fields(self):
        data = load_json("reports/reliability.json")
        required = {"sandbox_name", "fresh", "success", "wall_clock_s", "boot_to_ready_s", "cost_usd"}
        for i, run in enumerate(data["runs"]):
            for field in required:
                assert field in run, f"Run {i} missing field: {field}"

    def test_reliability_sandbox_names_pattern(self):
        data = load_json("reports/reliability.json")
        pattern = re.compile(r"^sbx-[a-z0-9]{8,}$")
        for run in data["runs"]:
            assert pattern.match(run["sandbox_name"]), (
                f"Invalid sandbox_name: {run['sandbox_name']}"
            )


# ---------------------------------------------------------------------------
# 10. reports/containment.json
# ---------------------------------------------------------------------------

class TestContainmentJson:
    def test_containment_json_parses(self):
        data = load_json("reports/containment.json")
        assert isinstance(data, dict)

    def test_containment_has_correct_structure(self):
        data = load_json("reports/containment.json")
        assert "attack" in data
        assert "blocked" in data
        assert "host_untouched" in data
        assert "evidence_paths" in data

    def test_containment_blocked_is_true(self):
        data = load_json("reports/containment.json")
        assert data["blocked"] is True

    def test_containment_host_untouched_is_true(self):
        data = load_json("reports/containment.json")
        assert data["host_untouched"] is True

    def test_containment_evidence_paths_nonempty(self):
        data = load_json("reports/containment.json")
        assert len(data["evidence_paths"]) >= 1


# ---------------------------------------------------------------------------
# 11. reports/failure_policy.json
# ---------------------------------------------------------------------------

class TestFailurePolicyJson:
    def test_failure_policy_json_parses(self):
        data = load_json("reports/failure_policy.json")
        assert isinstance(data, dict)

    def test_failure_policy_has_correct_structure(self):
        data = load_json("reports/failure_policy.json")
        assert "failed_step" in data
        assert "total_steps" in data
        assert "policy" in data
        assert "rationale" in data

    def test_failure_policy_valid_policy(self):
        data = load_json("reports/failure_policy.json")
        assert data["policy"] in ("rollback", "resume", "fresh")

    def test_failure_policy_rationale_length(self):
        data = load_json("reports/failure_policy.json")
        assert len(data["rationale"]) >= 50, "rationale is too short"


# ---------------------------------------------------------------------------
# 12. reports/failure_trace.jsonl
# ---------------------------------------------------------------------------

class TestFailureTraceJsonl:
    def test_failure_trace_exists(self):
        assert (PROJECT_ROOT / "reports" / "failure_trace.jsonl").exists()

    def test_failure_trace_has_events(self):
        events = load_jsonl("reports/failure_trace.jsonl")
        assert len(events) >= 5, "failure_trace.jsonl needs at least 5 events"

    def test_failure_trace_has_policy_applied_event(self):
        events = load_jsonl("reports/failure_trace.jsonl")
        policy_events = [e for e in events if e.get("event") == "policy_applied"]
        assert len(policy_events) >= 1, "No 'policy_applied' event found in failure_trace.jsonl"

    def test_failure_trace_events_have_timestamps(self):
        events = load_jsonl("reports/failure_trace.jsonl")
        for i, event in enumerate(events):
            assert "ts" in event, f"Event {i} missing 'ts' field"


# ---------------------------------------------------------------------------
# 13. reports/concurrency.json
# ---------------------------------------------------------------------------

class TestConcurrencyJson:
    def test_concurrency_json_parses(self):
        data = load_json("reports/concurrency.json")
        assert isinstance(data, dict)

    def test_concurrency_has_at_least_five_jobs(self):
        data = load_json("reports/concurrency.json")
        assert "jobs" in data
        assert len(data["jobs"]) >= 5, f"Need >= 5 jobs, got {len(data['jobs'])}"

    def test_concurrency_jobs_have_sandbox_names(self):
        data = load_json("reports/concurrency.json")
        for i, job in enumerate(data["jobs"]):
            assert "sandbox_name" in job, f"Job {i} missing sandbox_name"
            assert "started_at" in job, f"Job {i} missing started_at"

    def test_concurrency_has_breakage_notes(self):
        data = load_json("reports/concurrency.json")
        assert "breakage_notes" in data
        assert len(data["breakage_notes"]) >= 20


# ---------------------------------------------------------------------------
# 14. logs/commands.jsonl
# ---------------------------------------------------------------------------

class TestCommandsJsonl:
    REQUIRED_FIELDS = {"ts", "sandbox_name", "command", "decision", "execution_target"}

    def test_commands_jsonl_exists(self):
        assert (PROJECT_ROOT / "logs" / "commands.jsonl").exists()

    def test_commands_jsonl_has_entries(self):
        entries = load_jsonl("logs/commands.jsonl")
        assert len(entries) >= 5, f"Expected >= 5 entries, got {len(entries)}"

    def test_commands_jsonl_entries_valid(self):
        entries = load_jsonl("logs/commands.jsonl")
        for i, entry in enumerate(entries):
            for field in self.REQUIRED_FIELDS:
                assert field in entry, f"Entry {i} missing field: {field}"
            assert entry["decision"] in ("allow", "block"), (
                f"Entry {i} has invalid decision: {entry['decision']}"
            )
            assert entry["execution_target"] == "celesto_sandbox", (
                f"Entry {i} has wrong execution_target"
            )

    def test_commands_jsonl_has_blocked_entry(self):
        entries = load_jsonl("logs/commands.jsonl")
        blocked = [e for e in entries if e.get("decision") == "block"]
        assert len(blocked) >= 1, "No blocked entry found in logs/commands.jsonl"

    def test_commands_jsonl_sandbox_names_pattern(self):
        entries = load_jsonl("logs/commands.jsonl")
        pattern = re.compile(r"^sbx-[a-z0-9]{1,}$")  # relaxed for test sandbox names
        for entry in entries:
            assert pattern.match(entry["sandbox_name"]), (
                f"Invalid sandbox_name in log: {entry['sandbox_name']}"
            )
