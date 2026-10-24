import re
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, field_validator

VALID_STATES = ("created", "ready", "running", "succeeded", "failed", "deleted")
SANDBOX_RE = re.compile(r"^sbx-[a-z0-9]{8,}$")


class RunCreate(BaseModel):
    run_id: str
    sandbox_name: str
    problem_id: str
    state: Literal["created", "ready", "running", "succeeded", "failed", "deleted"]
    execution_target: str

    @field_validator("sandbox_name")
    @classmethod
    def validate_sandbox_name(cls, v: str) -> str:
        if not SANDBOX_RE.match(v):
            raise ValueError("sandbox_name must match ^sbx-[a-z0-9]{8,}$")
        return v

    @field_validator("execution_target")
    @classmethod
    def validate_execution_target(cls, v: str) -> str:
        if v != "celesto_sandbox":
            raise ValueError("execution_target must be 'celesto_sandbox'")
        return v


class RunOut(RunCreate):
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
