"""Phase 4: Compute Ragas metrics against the evaluation datasets.

Single responsibility: configure and run Ragas scoring.
Change when: metrics selection changes, judge LLM configuration changes,
or thresholds / pass-fail logic changes.
"""

from dataclasses import dataclass, field

import pandas as pd
from ragas import evaluate
from ragas.dataset_schema import EvaluationDataset
from ragas.metrics import Faithfulness, FactualCorrectness, ToolCallAccuracy
from ragas.llms import LangchainLLMWrapper


@dataclass
class ScoringConfig:
    """Configures which metrics to run and which LLM to use as judge.

    Attributes:
        judge_llm: Optional LangchainLLMWrapper pointing at your in-house LLM.
                   If None, Ragas uses its default (OpenAI).
        faithfulness_threshold: Minimum passing score for Faithfulness.
        factual_correctness_threshold: Minimum passing score for FactualCorrectness.
        tool_call_accuracy_threshold: Minimum passing score for ToolCallAccuracy.
    """
    judge_llm: LangchainLLMWrapper | None = None
    faithfulness_threshold: float = 0.7
    factual_correctness_threshold: float = 0.7
    tool_call_accuracy_threshold: float = 0.7


@dataclass
class ScoringResult:
    """Output of the scoring phase."""
    faithfulness: float
    factual_correctness: float
    tool_call_accuracy: float
    passed: bool
    raw: dict
    # Per-sample DataFrames — same row order as the datasets passed to compute_scores().
    # single_turn_samples: one row per invocation (columns: faithfulness, factual_correctness)
    # multiturn_samples:   one row per eval case  (column:  tool_call_accuracy)
    single_turn_samples: pd.DataFrame = field(default_factory=pd.DataFrame)
    multiturn_samples: pd.DataFrame = field(default_factory=pd.DataFrame)


def compute_scores(
    dataset: EvaluationDataset,
    multiturn_dataset: EvaluationDataset,
    config: ScoringConfig | None = None,
) -> ScoringResult:
    """Run Ragas metrics against both datasets.

    Args:
        dataset: SingleTurnSample dataset built by to_ragas_dataset().
        multiturn_dataset: MultiTurnSample dataset built by to_ragas_multiturn_dataset().
        config: Scoring configuration. Uses defaults if not provided.

    Returns:
        ScoringResult with per-metric scores and overall pass/fail.
    """
    if config is None:
        config = ScoringConfig()

    single_turn_metrics = [Faithfulness(), FactualCorrectness()]
    multiturn_metrics = [ToolCallAccuracy()]

    if config.judge_llm is not None:
        for metric in single_turn_metrics:
            metric.llm = config.judge_llm

    single_turn_result = evaluate(dataset=dataset, metrics=single_turn_metrics)
    single_turn_df = single_turn_result.to_pandas()
    single_turn_scores = single_turn_df.mean().to_dict()

    multiturn_result = evaluate(dataset=multiturn_dataset, metrics=multiturn_metrics)
    multiturn_df = multiturn_result.to_pandas()
    multiturn_scores = multiturn_df.mean().to_dict()

    faithfulness = single_turn_scores.get("faithfulness", 0.0)
    factual_correctness = single_turn_scores.get("factual_correctness", 0.0)
    tool_call_accuracy = multiturn_scores.get("tool_call_accuracy", 0.0)

    passed = (
        faithfulness >= config.faithfulness_threshold
        and factual_correctness >= config.factual_correctness_threshold
        and tool_call_accuracy >= config.tool_call_accuracy_threshold
    )

    return ScoringResult(
        faithfulness=faithfulness,
        factual_correctness=factual_correctness,
        tool_call_accuracy=tool_call_accuracy,
        passed=passed,
        raw={**single_turn_scores, **multiturn_scores},
        single_turn_samples=single_turn_df,
        multiturn_samples=multiturn_df,
    )
