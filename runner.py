"""Phase 2: Execute eval cases against the agent using ADK's Runner.

Single responsibility: run the agent turn-by-turn and collect raw outputs.
Change when: ADK Runner API changes, session setup changes, or event extraction
logic changes.
"""

from google.adk.agents import BaseAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.evaluation.eval_set import EvalCase, EvalSet
from google.adk.evaluation.eval_case import IntermediateData
from google.genai.types import Content, Part

from .model import CaseResult, InvocationResult


async def _run_single_case(
    runner: Runner,
    session_service: InMemorySessionService,
    eval_case: EvalCase,
    app_name: str,
    user_id: str,
) -> CaseResult:
    """Run all turns of a single eval case and collect outputs.

    Creates a fresh isolated session per eval case, mirroring the isolation
    behaviour of ADK's EvaluationGenerator.
    """
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        state=eval_case.session_input.state if eval_case.session_input else {},
    )

    case_result = CaseResult(eval_case_id=eval_case.eval_id)

    for turn_index, invocation in enumerate(eval_case.conversation):
        user_text = invocation.user_content.parts[0].text
        actual_response = ""
        tool_calls = []
        retrieved_contexts = []

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=Content(parts=[Part(text=user_text)], role="user"),
        ):
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if part.text:
                        actual_response += part.text

            if event.get_function_calls():
                for fc in event.get_function_calls():
                    tool_calls.append({"name": fc.name, "args": dict(fc.args)})

            if event.get_function_responses():
                for fr in event.get_function_responses():
                    # Tool responses become retrieved_contexts for Ragas
                    # Faithfulness checks response is grounded in these
                    retrieved_contexts.append(str(fr.response))

        reference_tool_calls = []
        if isinstance(invocation.intermediate_data, IntermediateData):
            reference_tool_calls = [
                {"name": fc.name, "args": dict(fc.args)}
                for fc in invocation.intermediate_data.tool_uses
            ]

        case_result.invocations.append(InvocationResult(
            eval_case_id=eval_case.eval_id,
            turn_index=turn_index,
            user_input=user_text,
            actual_response=actual_response,
            reference=invocation.final_response.parts[0].text,
            retrieved_contexts=retrieved_contexts,
            tool_calls=tool_calls,
            reference_tool_calls=reference_tool_calls,
        ))

    return case_result


async def run_eval_set(
    eval_set: EvalSet,
    agent: BaseAgent,
    app_name: str,
    user_id: str = "eval_user",
) -> list[CaseResult]:
    """Run all eval cases in the eval set against the given agent.

    Args:
        eval_set: The loaded EvalSet with cases to execute.
        agent: The ADK root agent to evaluate.
        app_name: Application name used for session scoping.
        user_id: User ID used for session scoping.

    Returns:
        List of CaseResult, one per eval_case, preserving original order.
    """
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name=app_name,
        session_service=session_service,
    )

    results = []
    for eval_case in eval_set.eval_cases:
        print(f"  [runner] eval_case={eval_case.eval_id} "
              f"({len(eval_case.conversation)} turns)")
        case_result = await _run_single_case(
            runner=runner,
            session_service=session_service,
            eval_case=eval_case,
            app_name=app_name,
            user_id=user_id,
        )
        results.append(case_result)

    return results
