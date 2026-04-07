"""Phase 1: Load an EvalSet from a .evalset.json file.

Single responsibility: deserialize the evalset file into ADK's EvalSet model.
Change when: evalset format changes or migration logic is needed.
"""

from pathlib import Path

from google.adk.evaluation.eval_set import EvalSet


def load_eval_set(path: str | Path) -> EvalSet:
    """Load and deserialize an evalset file into an EvalSet object.

    Args:
        path: Path to a .evalset.json file.

    Returns:
        Deserialized EvalSet with all eval_cases populated.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValidationError: If the file does not conform to the EvalSet schema.
    """
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Evalset file not found: {resolved}")

    return EvalSet.model_validate_json(resolved.read_text())
