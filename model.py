"""Internal data model shared across eval pipeline stages."""

from dataclasses import dataclass, field


@dataclass
class InvocationResult:
    """Holds actual outputs for a single agent invocation (one turn)."""

    eval_case_id: str
    turn_index: int
    user_input: str
    actual_response: str
    reference: str
    retrieved_contexts: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    reference_tool_calls: list[dict] = field(default_factory=list)


@dataclass
class CaseResult:
    """Holds all InvocationResults for a single eval case (all turns)."""

    eval_case_id: str
    invocations: list[InvocationResult] = field(default_factory=list)
