"""Phase 5: Publish evaluation results to Arize Phoenix as Experiments.

Single responsibility: upload eval cases as Phoenix Datasets and log per-turn
Ragas scores as Experiment evaluations.
Change when: Phoenix client API changes, dataset/experiment structure changes,
or new per-case metrics are added.

Phoenix concepts used:
  Dataset    — one per eval case; one Example per turn (user input, agent
               response, reference).
  Experiment — one per eval case per pipeline run, named {case_id}-{label}.
               Enables side-by-side comparison of prompt variants in the UI.
  Evaluators — faithfulness and factual_correctness are true per-turn scores;
               tool_call_accuracy is a case-level metric, same value for all
               turns of the case.

Requires: arize-phoenix-client>=2.0  (install via: uv sync --extra phoenix)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
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
    experiment_label: str = "",
) -> None:
    """Upload each eval case as a Phoenix Dataset and log Ragas scores as an Experiment.

    One Dataset per eval case (named after the case ID) is created on first run
    and reused on subsequent runs. Each pipeline run creates one new Experiment
    per case, named {case_id}-{experiment_label}, enabling prompt A/B comparison
    in the Phoenix UI.

    Args:
        result: Aggregate + per-sample scoring output from compute_scores().
        case_results: Per-case invocation details from run_eval_set().
        config: Phoenix connection settings. Uses defaults if not provided.
        experiment_label: Human-readable label for this run, e.g. "prompt-v2".
                          Defaults to a UTC timestamp if empty.
    """
    from phoenix.client import Client
    from phoenix.client.experiments import run_experiment

    if config is None:
        config = PhoenixConfig()

    label = experiment_label or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    client = Client(endpoint=config.endpoint)
    per_turn_scores = _build_per_turn_scores(result, case_results)

    for case in case_results:
        dataset = _create_or_get_dataset(client, case)
        _run_experiment(client, run_experiment, dataset, case.eval_case_id, label, per_turn_scores)


# ── helpers ──────────────────────────────────────────────────────────────────

def _create_or_get_dataset(client, case: CaseResult):
    """Create a Phoenix Dataset for a case, or reuse it if it already exists."""
    try:
        return client.datasets.create_dataset(
            name=case.eval_case_id,
            dataframe=_build_case_df(case),
            input_keys=["user_input"],
            output_keys=["agent_response", "reference"],
            metadata_keys=["case_id", "turn_index"],
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 409:
            raise
        return client.datasets.get_dataset(dataset=case.eval_case_id)


def _run_experiment(
    client,
    run_experiment_fn,
    dataset,
    case_id: str,
    label: str,
    per_turn_scores: dict[tuple[str, int], dict[str, float]],
) -> None:
    """Run a Phoenix Experiment for a single eval case."""

    def _key(metadata) -> tuple[str, int]:
        # turn_index is stored as int but Phoenix may deserialize it as float via JSON.
        return (metadata["case_id"], int(metadata["turn_index"]))

    def _score(metadata, metric: str) -> float:
        value = per_turn_scores.get(_key(metadata), {}).get(metric)
        if value is None:
            raise ValueError(f"no {metric} score for {_key(metadata)}")
        return value

    def task(example) -> str:
        return example["output"]["agent_response"]

    def faithfulness(metadata: dict[str, Any]) -> float:
        return _score(metadata, "faithfulness")

    def factual_correctness(metadata: dict[str, Any]) -> float:
        return _score(metadata, "factual_correctness")

    def tool_call_accuracy__case(metadata: dict[str, Any]) -> float:
        """Case-level metric repeated per turn. Same value for all turns in a case."""
        return _score(metadata, "tool_call_accuracy")

    run_experiment_fn(
        dataset=dataset,
        task=task,
        evaluators=[faithfulness, factual_correctness, tool_call_accuracy__case],
        experiment_name=f"{case_id}-{label}",
        client=client,
    )


def _build_case_df(case: CaseResult) -> pd.DataFrame:
    """One row per turn for a single eval case."""
    return pd.DataFrame([
        {
            "case_id": case.eval_case_id,
            "turn_index": inv.turn_index,
            "user_input": inv.user_input,
            "agent_response": inv.actual_response,
            "reference": inv.reference,
        }
        for inv in case.invocations
    ])


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
