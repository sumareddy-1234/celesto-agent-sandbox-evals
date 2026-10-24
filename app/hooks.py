"""
Command safety hooks — every command the agent wishes to run is passed through
check_command() before it reaches the Celesto guest.  The hook logs the attempt
and can block commands by raising CommandBlockedError.
"""
import json
import os
import re
from datetime import datetime, timezone

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "commands.jsonl")

BLOCKED_PATTERNS = [
    re.compile(r"rm\s+-rf\s+/"),            # destructive root wipe
    re.compile(r"curl.*\$[A-Z_]+"),         # potential exfiltration with env vars
    re.compile(r"wget.*\$[A-Z_]+"),         # same via wget
    re.compile(r"cat\s+.*\.env"),           # reading secret files
    re.compile(r"export.*SECRET"),          # exporting sensitive vars
]


class CommandBlockedError(Exception):
    """Raised when a command is blocked by a safety hook."""


def check_command(command: str, sandbox_name: str) -> None:
    """
    Inspect the command before execution.
    Raises CommandBlockedError if the command matches a disallowed pattern.
    Always writes an audit line to logs/commands.jsonl.
    """
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    decision = "allow"
    for pattern in BLOCKED_PATTERNS:
        if pattern.search(command):
            decision = "block"
            break

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "sandbox_name": sandbox_name,
        "command": command,
        "decision": decision,
        "execution_target": "celesto_sandbox",
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    if decision == "block":
        raise CommandBlockedError(f"Command blocked by safety hook: {command!r}")
