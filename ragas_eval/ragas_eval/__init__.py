"""Ragas evaluation pipeline for ADK agents.

Five-phase pipeline:
  1. loader           — deserialize .evalset.json → EvalSet
  2. runner           — run agent turn-by-turn → List[CaseResult]
  3. transformer      — map to Ragas dataset schemas
  4. scorer           — compute Faithfulness, FactualCorrectness, ToolCallAccuracy
  5. phoenix_reporter — publish results to Arize Phoenix via OpenTelemetry (optional)
"""
