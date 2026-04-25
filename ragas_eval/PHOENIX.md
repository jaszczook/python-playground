# Phoenix Nomenclature

How `ragas_eval` concepts map to Arize Phoenix.

## Mapping

| ragas_eval | Phoenix | Granularity |
|---|---|---|
| eval case (`eval_id`) | **Dataset** | one per eval case |
| single agent turn (`InvocationResult`) | **Example** | one per turn within a case |
| one full pipeline run | **Experiment** per case | one per case per `run_ragas.py` invocation |
| per-turn Ragas scores | **Experiment Run** | one per Example per Experiment |

## Concrete example — `sample.evalset.json`

### Dataset: `case_weather_lookup` (1 Example, stable across runs)

| Example | `turn_index` | `user_input` |
|---|---|---|
| #1 | 0 | "What is the weather like in Warsaw today?" |

| Experiment | faithfulness | factual_correctness | tool_call_accuracy |
|---|---|---|---|
| `case_weather_lookup-prompt-v1` | 0.92 | 0.85 | 0.80 |
| `case_weather_lookup-prompt-v2` | 0.95 | 0.91 | 1.00 |

---

### Dataset: `case_multi_turn_booking` (2 Examples, stable across runs)

| Example | `turn_index` | `user_input` |
|---|---|---|
| #1 | 0 | "What is the weather in Paris?" |
| #2 | 1 | "Book me a hotel for 2 nights starting tomorrow." |

| Experiment | Example | faithfulness | factual_correctness | tool_call_accuracy |
|---|---|---|---|---|
| `case_multi_turn_booking-prompt-v1` | #1 | 0.95 | 0.90 | 0.75 |
| `case_multi_turn_booking-prompt-v1` | #2 | 0.88 | 0.84 | 0.75 |
| `case_multi_turn_booking-prompt-v2` | #1 | 0.97 | 0.93 | 1.00 |
| `case_multi_turn_booking-prompt-v2` | #2 | 0.94 | 0.89 | 1.00 |

`tool_call_accuracy` is a case-level metric (computed over the full conversation),
so it has the same value for all turns within a case.

## Usage

```bash
# Label the experiment with a prompt variant name for easy comparison in Phoenix UI
uv run python run_ragas.py examples/sample.evalset.json \
  --phoenix-endpoint http://localhost:6006 \
  --experiment-label prompt-v2

# Replay from a pickle snapshot
uv run python debug_phoenix.py --label prompt-v2
```

## Why Example = turn (not eval case)

`faithfulness` and `factual_correctness` are per-turn metrics — aggregating them
to case level before storing discards exactly the information Phoenix is useful for:
which specific turn failed and by how much. `tool_call_accuracy` is the one
case-level metric and is repeated across all turns of its case.
