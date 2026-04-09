"""Ragas evaluation pipeline for ADK agents.

Four-phase pipeline:
  1. loader      — deserialize .evalset.json → EvalSet
  2. runner      — run agent turn-by-turn → List[CaseResult]
  3. transformer — map to Ragas dataset schemas
  4. scorer      — compute Faithfulness, FactualCorrectness, ToolCallAccuracy
"""
