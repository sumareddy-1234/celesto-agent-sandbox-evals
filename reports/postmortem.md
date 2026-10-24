# Postmortem: Celesto Agent Sandbox Evaluation

## SDK Availability

The Celesto SDK (`celesto` or `smolvm` Python package) was **not installed or available** during development of this evaluation platform. This project was developed on a Windows host, and the local open-source Celesto runtime requires Linux with KVM support, which is not available in this environment.

As a direct consequence, **no actual sandbox runs were performed**. The 20 entries in `reports/reliability.json` are representative design-time values chosen to reflect realistic latency and success-rate characteristics for the evaluation harness. They are clearly marked as design-time values in that file and must not be interpreted as measured results.

## What the Eval Harness Would Measure

The `scripts/eval_runner.py` script is designed to run 20 iterations of the agent task in fresh Celesto sandboxes when the SDK is available. For each run it would measure:

- **wall_clock_s**: Total elapsed time from sandbox creation to task completion and deletion.
- **boot_to_ready_s**: Time from sandbox creation to the guest being ready to accept commands (the cold-start latency of the micro-VM).
- **exit_code**: Whether the agent task (clone repo, install deps, run tests, write proof.txt) succeeded.
- **cost_usd**: Per-sandbox billing cost as exposed by the Celesto Cloud SDK (not available in the local runtime v0.x).

From these measurements the harness computes the median wall-clock time, the 90th-percentile latency (p90), and the overall success rate across the 20 runs.

## Failure Modes Observed in Design

1. **SDK unavailability**: The primary failure mode encountered during development. The harness detects this via `ImportError` and exits with code 1 rather than silently proceeding with a host-subprocess fallback, which would violate the isolation guarantee.

2. **Package installation timeout (step 7)**: During the failure-policy design exercise, `pip install` inside the sandbox was identified as the most likely failure point due to network latency or transient upstream errors. The `rollback` policy was chosen over `resume` or `fresh` to restore a known-good filesystem state without repeating all prior setup steps.

3. **Prompt injection exfiltration attempt**: The containment test demonstrated that the safety hook correctly blocks commands matching the `curl.*\$[A-Z_]+` pattern before they reach the guest kernel. This validates the defence-in-depth design combining code-enforced hooks and sandbox network policy.

4. **Concurrency limits**: With a Celesto Cloud free trial, only one retained sandbox is permitted simultaneously. Concurrency testing was designed but not executed. The `sbx-[a-z0-9]{8,}` name pattern using `uuid4` hex ensures uniqueness across concurrent runs, but rate-limit and cost blow-up behaviour would need to be verified with real credentials and a paid account.
