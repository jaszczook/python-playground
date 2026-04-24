"""Phase 5: Publish evaluation results to Arize Phoenix as an Experiment.

Single responsibility: upload eval cases as a Phoenix Dataset and log per-turn
Ragas scores as Experiment evaluations.
Change when: Phoenix client API changes, dataset/experiment structure changes,
or new per-case metrics are added.

Phoenix concepts used:
  Dataset    — one row per turn; stores the user input, agent response, and reference.
  Experiment — a named run against a dataset; stores task outputs and evaluation scores.
               faithfulness and factual_correctness are true per-turn scores.
               tool_call_accuracy is a case-level metric repeated across all turns
               of the same case (label makes this clear in the UI).

Requires: arize-phoenix-client>=2.0  (install via: uv sync --extra phoenix)
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
    from phoenix.client import Client
    from phoenix.client.experiments import run_experiment

    if config is None:
        config = PhoenixConfig()

    client = Client(endpoint=config.endpoint)
    per_turn_scores = _build_per_turn_scores(result, case_results)

    dataset_name = Path(evalset_path).stem if evalset_path else "ragas-evalset"
    dataset = client.datasets.create_dataset(
        name=dataset_name,
        dataframe=_build_dataset_df(case_results),
        input_keys=["user_input"],
        output_keys=["agent_response", "reference"],
        metadata_keys=["case_id", "turn_index"],
    )

    # DatasetExample is a TypedDict: access fields with example["key"].
    def task(example) -> str:
        return example["output"]["agent_response"]

    def faithfulness(output, metadata) -> float | None:
        return per_turn_scores.get(
            (metadata["case_id"], metadata["turn_index"]), {}
        ).get("faithfulness")

    def factual_correctness(output, metadata) -> float | None:
        return per_turn_scores.get(
            (metadata["case_id"], metadata["turn_index"]), {}
        ).get("factual_correctness")

    def tool_call_accuracy__case(output, metadata) -> float | None:
        """Case-level metric repeated per turn. Same value for all turns in a case."""
        return per_turn_scores.get(
            (metadata["case_id"], metadata["turn_index"]), {}
        ).get("tool_call_accuracy")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_experiment(
        dataset=dataset,
        task=task,
        evaluators=[faithfulness, factual_correctness, tool_call_accuracy__case],
        experiment_name=f"{dataset_name}-{timestamp}",
        client=client,
    )


# ── helpers ──────────────────────────────────────────────────────────────────

def _build_dataset_df(case_results: list[CaseResult]) -> pd.DataFrame:
    """One row per turn with the user input, agent response, and reference."""
    rows = []
    for case in case_results:
        for inv in case.invocations:
            rows.append({
                "case_id": case.eval_case_id,
                "turn_index": inv.turn_index,
                "user_input": inv.user_input,
                "agent_response": inv.actual_response,
                "reference": inv.reference,
            })
    return pd.DataFrame(rows)


def _build_per_turn_scores(
    result: ScoringResult,
    case_results: list[CaseResult],
) -> dict[tuple[str, int], dict[str, float]]:
    """Build a {(case_id, turn_index) → {metric → score}} dict.

    single_turn_samples has one row per invocation in the same order as
    transformer output (case_results flattened turn-by-turn).
    multiturn_samples has one row per case; tool_call_accuracy is repeated
    across all turns of that case.
    """
    scores: dict[tuple[str, int], dict[str, float]] = {}

    # Flatten turns to get the (case_id, turn_index) key for each st row.
    turn_keys: list[tuple[str, int]] = [
        (case.eval_case_id, inv.turn_index)
        for case in case_results
        for inv in case.invocations
    ]

    # ── single-turn metrics (one value per turn, direct from scorer) ──────────
    if not result.single_turn_samples.empty:
        st_df = result.single_turn_samples
        st_cols = [c for c in ("faithfulness", "factual_correctness") if c in st_df.columns]
        for i, key in enumerate(turn_keys):
            scores.setdefault(key, {}).update(
                {col: float(st_df.iloc[i][col]) for col in st_cols}
            )

    # ── multi-turn metric (case-level, repeated per turn) ─────────────────────
    if not result.multiturn_samples.empty:
        mt_df = result.multiturn_samples
        if "tool_call_accuracy" in mt_df.columns:
            for case_idx, case in enumerate(case_results):
                tca = float(mt_df.iloc[case_idx]["tool_call_accuracy"])
                for inv in case.invocations:
                    scores.setdefault((case.eval_case_id, inv.turn_index), {})["tool_call_accuracy"] = tca

    return scores
