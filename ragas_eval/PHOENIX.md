# Phoenix Nomenclature

How `ragas_eval` concepts map to Arize Phoenix.

## Mapping

| ragas_eval | Phoenix | Granularity |
|---|---|---|
| `.evalset.json` file | **Dataset** | one per evalset file |
| single agent turn (`InvocationResult`) | **Example** | one per turn |
| one full pipeline run | **Experiment** | one per `run_ragas.py` invocation |
| per-turn Ragas scores | **Experiment Run** | one per Example per Experiment |

## Concrete example — `sample.evalset.json`

The evalset has 3 eval cases and 4 turns total.

### Dataset: `sample` (created once, reused across runs)

| Example | `case_id` | `turn_index` | `user_input` |
|---|---|---|---|
| #1 | `case_weather_lookup` | 0 | "What is the weather like in Warsaw today?" |
| #2 | `case_flight_search` | 0 | "Find me flights from Warsaw to London next Monday." |
| #3 | `case_multi_turn_booking` | 0 | "What is the weather in Paris?" |
| #4 | `case_multi_turn_booking` | 1 | "Great, book me a hotel there for 2 nights starting tomorrow." |

### Experiment: `sample-20240424T120000` (one per run)

Each run creates a new timestamped Experiment against the same Dataset.
Each Experiment produces 4 Experiment Runs — one per Example — with these scores:

| Experiment Run | faithfulness | factual_correctness | tool_call_accuracy |
|---|---|---|---|
| Example #1 | ✓ per-turn | ✓ per-turn | repeated from `case_weather_lookup` |
| Example #2 | ✓ per-turn | ✓ per-turn | repeated from `case_flight_search` |
| Example #3 | ✓ per-turn | ✓ per-turn | repeated from `case_multi_turn_booking` |
| Example #4 | ✓ per-turn | ✓ per-turn | same as #3 (case-level metric) |

`tool_call_accuracy` is a case-level metric computed by Ragas over the full conversation,
so it has the same value for all turns belonging to the same eval case.

## Why Example = turn (not eval case)

`faithfulness` and `factual_correctness` are per-turn metrics. Aggregating them to case
level before storing would discard exactly the information Phoenix is useful for: which
specific turn failed and by how much. `tool_call_accuracy` is the one case-level metric;
it is repeated across all turns of a case with a label that makes this clear in the UI.
