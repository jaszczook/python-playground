"""Replay only the Phoenix publish phase from a pickled snapshot.

Snapshot inputs in IntelliJ Evaluate Expression (set breakpoint after Phase 4
in run_ragas.py, i.e. after compute_scores() returns):

    import pickle; pickle.dump((result, case_results), open('/tmp/phoenix_inputs.pkl', 'wb'))

Then run:

    cd ragas_eval
    uv run python debug_phoenix.py
    uv run python debug_phoenix.py --endpoint http://localhost:6006 --project my-project --label prompt-v2
"""

import argparse
import pickle

from ragas_eval.phoenix_reporter import PhoenixConfig, publish_to_phoenix


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay Phoenix publish from pickle snapshot")
    parser.add_argument("--snapshot", default="/tmp/phoenix_inputs.pkl",
                        help="Path to pickle file containing (result, case_results)")
    parser.add_argument("--endpoint", default="http://localhost:6006",
                        help="Phoenix base URL")
    parser.add_argument("--project", default="ragas-eval",
                        help="Phoenix project name")
    parser.add_argument("--label", default="",
                        help="Experiment label, e.g. 'prompt-v2'. Defaults to UTC timestamp.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print(f"Loading snapshot: {args.snapshot}")
    with open(args.snapshot, "rb") as f:
        result, case_results = pickle.load(f)

    print(f"  {len(case_results)} cases loaded")
    print(f"  faithfulness={result.faithfulness:.4f}  "
          f"factual_correctness={result.factual_correctness:.4f}  "
          f"tool_call_accuracy={result.tool_call_accuracy:.4f}")

    config = PhoenixConfig(endpoint=args.endpoint, project_name=args.project)
    print(f"\nPublishing to Phoenix at {args.endpoint} (project={args.project!r})...")
    publish_to_phoenix(
        result=result,
        case_results=case_results,
        config=config,
        experiment_label=args.label,
    )
    print("Done.")


if __name__ == "__main__":
    main()
