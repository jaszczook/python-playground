"""Entry point: run the Ragas eval pipeline against an evalset file.

Usage:
    python run_ragas.py <path_to_evalset.json> [--threshold-faithfulness 0.7]
                                               [--threshold-factual 0.7]
                                               [--app-name my_app]

Exit codes:
    0  all metrics passed thresholds
    1  one or more metrics below threshold  (useful for CI gate)
"""

import asyncio
import argparse
import json
import sys

from ragas_eval.loader import load_eval_set
from ragas_eval.runner import run_eval_set
from ragas_eval.transformer import to_ragas_dataset, to_ragas_multiturn_dataset
from ragas_eval.scorer import ScoringConfig, compute_scores

# Import your agent — adjust path to match your project layout
from my_app.agent import root_agent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Ragas eval pipeline")
    parser.add_argument("evalset", help="Path to .evalset.json file")
    parser.add_argument("--app-name", default="my_app")
    parser.add_argument("--threshold-faithfulness", type=float, default=0.7)
    parser.add_argument("--threshold-factual", type=float, default=0.7)
    parser.add_argument("--threshold-tool-call-accuracy", type=float, default=0.7)
    return parser.parse_args()


async def run_pipeline(args: argparse.Namespace) -> bool:
    """Execute all four pipeline phases. Returns True if passed."""

    # Phase 1 — Load
    print(f"\n[1/4] Loading evalset: {args.evalset}")
    eval_set = load_eval_set(args.evalset)
    print(f"      {len(eval_set.eval_cases)} eval cases loaded")

    # Phase 2 — Infer
    print(f"\n[2/4] Running agent inference ({args.app_name})...")
    case_results = await run_eval_set(
        eval_set=eval_set,
        agent=root_agent,
        app_name=args.app_name,
    )
    total_turns = sum(len(c.invocations) for c in case_results)
    print(f"      {total_turns} invocations collected")

    # Phase 3 — Transform
    print("\n[3/4] Building Ragas datasets...")
    dataset = to_ragas_dataset(case_results)
    multiturn_dataset = to_ragas_multiturn_dataset(case_results)
    print(f"      {len(dataset.samples)} single-turn samples, "
          f"{len(multiturn_dataset.samples)} multi-turn samples prepared")

    # Phase 4 — Score
    print("\n[4/4] Computing Ragas metrics...")
    config = ScoringConfig(
        faithfulness_threshold=args.threshold_faithfulness,
        factual_correctness_threshold=args.threshold_factual,
        tool_call_accuracy_threshold=args.threshold_tool_call_accuracy,
    )
    result = compute_scores(dataset=dataset, multiturn_dataset=multiturn_dataset, config=config)

    # Report
    print("\n" + "=" * 40)
    print("RAGAS EVALUATION RESULTS")
    print("=" * 40)
    print(json.dumps({
        "faithfulness": round(result.faithfulness, 4),
        "factual_correctness": round(result.factual_correctness, 4),
        "tool_call_accuracy": round(result.tool_call_accuracy, 4),
        "passed": result.passed,
        "thresholds": {
            "faithfulness": args.threshold_faithfulness,
            "factual_correctness": args.threshold_factual,
            "tool_call_accuracy": args.threshold_tool_call_accuracy,
        },
    }, indent=2))
    print("=" * 40)
    print(f"RESULT: {'✓ PASSED' if result.passed else '✗ FAILED'}")

    return result.passed


def main() -> None:
    args = parse_args()
    passed = asyncio.run(run_pipeline(args))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
