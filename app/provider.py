"""
Celesto sandbox provider adapter.

When CELESTO_PROVIDER=local the runtime uses the open-source Celesto SDK
(or falls back to a clearly labelled mock if the SDK is not installed /
credentials are absent).

When CELESTO_PROVIDER=cloud it connects to Celesto Cloud.

IMPORTANT: This module never silently substitutes subprocess.run on the host.
If the SDK is unavailable it raises CelestoUnavailableError; callers can
catch that and record the run as skipped rather than succeeded.
"""
import os
import time
import uuid
from datetime import datetime, timezone

from .hooks import check_command, CommandBlockedError

PROVIDER = os.environ.get("CELESTO_PROVIDER", "local")
API_KEY = os.environ.get("CELESTO_API_KEY", "")


class CelestoUnavailableError(Exception):
    """Raised when the Celesto SDK/runtime is not available."""


def _make_sandbox_name() -> str:
    uid = uuid.uuid4().hex[:12]
    return f"sbx-{uid}"


def run_in_sandbox(
    command: str,
    sandbox_name: str | None = None,
    block_network: bool = False,
) -> dict:
    """
    Execute *command* inside a fresh Celesto sandbox.

    Returns a dict with:
        sandbox_name, command, exit_code, stdout, stderr,
        boot_to_ready_s, wall_clock_s, cost_usd, blocked
    """
    if sandbox_name is None:
        sandbox_name = _make_sandbox_name()

    # Safety hook — may raise CommandBlockedError
    try:
        check_command(command, sandbox_name)
    except CommandBlockedError:
        return {
            "sandbox_name": sandbox_name,
            "command": command,
            "exit_code": -1,
            "stdout": "",
            "stderr": "Command blocked by safety hook",
            "boot_to_ready_s": 0.0,
            "wall_clock_s": 0.0,
            "cost_usd": 0.0,
            "blocked": True,
        }

    t_start = time.monotonic()

    try:
        # Attempt real SDK import
        try:
            from smolvm import Computer  # type: ignore
            sdk_name = "smolvm"
        except ImportError:
            try:
                from celesto import Computer  # type: ignore
                sdk_name = "celesto"
            except ImportError:
                raise CelestoUnavailableError(
                    "Neither 'celesto' nor 'smolvm' SDK is installed. "
                    "Install with: pip install celesto"
                )

        t_boot_start = time.monotonic()
        with Computer(name=sandbox_name) as computer:
            boot_to_ready_s = time.monotonic() - t_boot_start
            result = computer.run(command)
            wall_clock_s = time.monotonic() - t_start

        return {
            "sandbox_name": sandbox_name,
            "command": command,
            "exit_code": result.exit_code,
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
            "boot_to_ready_s": round(boot_to_ready_s, 3),
            "wall_clock_s": round(wall_clock_s, 3),
            "cost_usd": 0.0,   # Cloud billing not exposed in SDK v0.x
            "blocked": False,
        }

    except CelestoUnavailableError:
        raise
    except Exception as exc:
        wall_clock_s = time.monotonic() - t_start
        return {
            "sandbox_name": sandbox_name,
            "command": command,
            "exit_code": 1,
            "stdout": "",
            "stderr": str(exc),
            "boot_to_ready_s": 0.0,
            "wall_clock_s": round(wall_clock_s, 3),
            "cost_usd": 0.0,
            "blocked": False,
        }
