"""Phase 3: Transform CaseResults into Ragas evaluation datasets.

Single responsibility: map the internal model to Ragas' expected schemas.
Change when: Ragas schema changes, or new metrics requiring different fields
are introduced.
"""

from ragas.dataset_schema import EvaluationDataset, MultiTurnSample, SingleTurnSample
from ragas.messages import AIMessage, HumanMessage, ToolCall

from .model import CaseResult


def to_ragas_dataset(case_results: list[CaseResult]) -> EvaluationDataset:
    """Convert a list of CaseResults into a Ragas EvaluationDataset of SingleTurnSamples.

    Each invocation (turn) becomes one SingleTurnSample. Used for Faithfulness
    and FactualCorrectness metrics.

    Ragas field mapping:
        user_input         ← InvocationResult.user_input
        response           ← InvocationResult.actual_response
        reference          ← InvocationResult.reference
        retrieved_contexts ← InvocationResult.retrieved_contexts
    """
    samples = []
    for case_result in case_results:
        for inv in case_result.invocations:
            samples.append(SingleTurnSample(
                user_input=inv.user_input,
                response=inv.actual_response,
                reference=inv.reference,
                retrieved_contexts=inv.retrieved_contexts,
            ))
    return EvaluationDataset(samples=samples)


def to_ragas_multiturn_dataset(case_results: list[CaseResult]) -> EvaluationDataset:
    """Convert a list of CaseResults into a Ragas EvaluationDataset of MultiTurnSamples.

    Each case becomes one MultiTurnSample containing all of its turns as an
    alternating sequence of HumanMessage / AIMessage. Used for ToolCallAccuracy.

    Ragas field mapping:
        user_input (messages)  ← alternating HumanMessage / AIMessage per turn
        AIMessage.tool_calls   ← InvocationResult.tool_calls  (actual)
        reference_tool_calls   ← InvocationResult.reference_tool_calls (expected, flat)
    """
    samples = []
    for case_result in case_results:
        messages = []
        reference_tool_calls = []

        for inv in case_result.invocations:
            messages.append(HumanMessage(content=inv.user_input))

            actual_tool_calls = [
                ToolCall(name=tc["name"], args=tc.get("args", {}))
                for tc in inv.tool_calls
            ]
            messages.append(AIMessage(
                content=inv.actual_response,
                tool_calls=actual_tool_calls if actual_tool_calls else None,
            ))

            reference_tool_calls.extend(
                ToolCall(name=tc["name"], args=tc.get("args", {}))
                for tc in inv.reference_tool_calls
            )

        samples.append(MultiTurnSample(
            user_input=messages,
            reference_tool_calls=reference_tool_calls if reference_tool_calls else None,
        ))

    return EvaluationDataset(samples=samples)
