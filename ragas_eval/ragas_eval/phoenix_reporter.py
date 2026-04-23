"""Phase 5: Publish evaluation results to Arize Phoenix as an Experiment.

Single responsibility: upload eval cases as a Phoenix Dataset and log per-case
Ragas scores as Experiment evaluations.
Change when: Phoenix client API changes, dataset/experiment structure changes,
or new per-case metrics are added.

Phoenix concepts used:
  Dataset    — one row per eval case; stores the input conversation and reference.
  Experiment — a named run against a dataset; stores task outputs and evaluation scores.
               Each evaluation (faithfulness, factual_correctness, tool_call_accuracy)
               appears as a separate column in the Phoenix Experiments UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ragas_eval.model import CaseResult
from ragas_eval.scorer import ScoringResult


@dataclass
class PhoenixConfig:
    """Configuration for publishing to a Phoenix instance.

    Attributes:
        endpoint: Base URL of the Phoenix instance, e.g. "http://localhost:6006".
        project_name: Phoenix project to publish into.
    """
    endpoint: str = "http://localhost:6006"
    project_name: str = "ragas-eval"


def publish_to_phoenix(
    result: ScoringResult,
    case_results: list[CaseResult],
    config: PhoenixConfig | None = None,
    evalset_path: str = "",
) -> None:
    """Upload eval cases as a Phoenix Dataset and log Ragas scores as an Experiment.

    Args:
        result: Aggregate + per-sample scoring output from compute_scores().
        case_results: Per-case invocation details from run_eval_set().
        config: Phoenix connection settings. Uses defaults if not provided.
        evalset_path: Path to the evalset file, used to name the dataset.
    """
    # Import here so the dependency is only required when Phoenix reporting is used.
    import phoenix as px
    from phoenix.experiments import run_experiment
    from phoenix.experiments.types import EvaluationResult as PhoenixEval

    if config is None:
        config = PhoenixConfig()

    client = px.Client(endpoint=config.endpoint)
    per_case_scores = _build_per_case_scores(result, case_results)

    dataset_name = Path(evalset_path).stem if evalset_path else "ragas-evalset"
    dataset = client.upload_dataset(
        dataframe=_build_dataset_df(case_results),
        dataset_name=dataset_name,
        input_keys=["conversation"],
        output_keys=["reference"],
        metadata_keys=["case_id", "num_turns"],
    )

    # Pre-computed response lookup: last turn's actual output per case.
    response_by_case = {
        case.eval_case_id: case.invocations[-1].actual_response
        for case in case_results
        if case.invocations
    }

    def task(example) -> str:
        return response_by_case.get(example.metadata["case_id"], "")

    def faithfulness(output, metadata) -> PhoenixEval:
        score = per_case_scores.get(metadata["case_id"], {}).get("faithfulness")
        return PhoenixEval(score=score)

    def factual_correctness(output, metadata) -> PhoenixEval:
        score = per_case_scores.get(metadata["case_id"], {}).get("factual_correctness")
        return PhoenixEval(score=score)

    def tool_call_accuracy(output, metadata) -> PhoenixEval:
        score = per_case_scores.get(metadata["case_id"], {}).get("tool_call_accuracy")
        return PhoenixEval(score=score)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_experiment(
        dataset=dataset,
        task=task,
        evaluators=[faithfulness, factual_correctness, tool_call_accuracy],
        experiment_name=f"{dataset_name}-{timestamp}",
        project_name=config.project_name,
        client=client,
    )


# ── helpers ──────────────────────────────────────────────────────────────────

def _build_dataset_df(case_results: list[CaseResult]) -> pd.DataFrame:
    """One row per eval case with the full conversation and the final reference."""
    rows = []
    for case in case_results:
        turns = []
        for inv in case.invocations:
            turns.append(f"User: {inv.user_input}")
            turns.append(f"Agent: {inv.actual_response}")
        rows.append({
            "case_id": case.eval_case_id,
            "num_turns": len(case.invocations),
            "conversation": "\n".join(turns),
            "reference": case.invocations[-1].reference if case.invocations else "",
        })
    return pd.DataFrame(rows)


def _build_per_case_scores(
    result: ScoringResult,
    case_results: list[CaseResult],
) -> dict[str, dict[str, float]]:
    """Build a {case_id → {metric → score}} dict from the per-sample DataFrames.

    single_turn_samples has one row per invocation (same order as transformer output).
    multiturn_samples has one row per case (same order as case_results).
    We average single-turn metrics across turns within each case.
    """
    scores: dict[str, dict[str, float]] = {}

    # ── single-turn metrics (averaged per case) ───────────────────────────────
    if not result.single_turn_samples.empty:
        st_df = result.single_turn_samples.copy()
        st_df["case_id"] = [
            case.eval_case_id
            for case in case_results
            for _ in case.invocations
        ]
        st_cols = [c for c in ("faithfulness", "factual_correctness") if c in st_df.columns]
        if st_cols:
            for case_id, row in st_df.groupby("case_id")[st_cols].mean().iterrows():
                scores.setdefault(str(case_id), {}).update(
                    {k: float(v) for k, v in row.items()}
                )

    # ── multi-turn metrics (one value per case) ────────────────────────────────
    if not result.multiturn_samples.empty:
        mt_df = result.multiturn_samples.copy()
        mt_df["case_id"] = [case.eval_case_id for case in case_results]
        mt_cols = [c for c in ("tool_call_accuracy",) if c in mt_df.columns]
        if mt_cols:
            for _, row in mt_df[["case_id"] + mt_cols].iterrows():
                case_id = str(row["case_id"])
                scores.setdefault(case_id, {}).update(
                    {k: float(row[k]) for k in mt_cols}
                )

    return scores
