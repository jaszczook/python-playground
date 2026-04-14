"""Phase 1: Load an EvalSet from a .evalset.json file.

Single responsibility: deserialize the evalset file into ADK's EvalSet model.
Change when: evalset format changes or migration logic is needed.
"""

import base64
import json
from pathlib import Path

from google.adk.evaluation.eval_set import EvalSet


def _resolve_local_files(raw: dict, base_dir: Path) -> dict:
    """Replace file:// file_data parts with inline_data (base64-encoded).

    Allows evalset JSON to reference local repo files via:
        {"file_data": {"mime_type": "...", "file_uri": "file://relative/path"}}

    which is resolved to:
        {"inline_data": {"mime_type": "...", "data": "<base64>"}}

    before ADK parses the evalset. This avoids embedding raw base64 in the
    evalset JSON while not requiring the Gemini Files API.
    """
    for case in raw.get("eval_cases", []):
        for invocation in case.get("conversation", []):
            for part in invocation.get("user_content", {}).get("parts", []):
                fd = part.get("file_data")
                if not (fd and isinstance(fd.get("file_uri"), str) and fd["file_uri"].startswith("file://")):
                    continue
                rel_path = fd["file_uri"][len("file://"):]
                file_path = base_dir / rel_path
                if not file_path.exists():
                    raise FileNotFoundError(f"Local file referenced in evalset not found: {file_path}")
                file_bytes = file_path.read_bytes()
                part.pop("file_data")
                part["inline_data"] = {
                    "mime_type": fd["mime_type"],
                    "data": base64.b64encode(file_bytes).decode(),
                }
    return raw


def load_eval_set(path: str | Path) -> EvalSet:
    """Load and deserialize an evalset file into an EvalSet object.

    Args:
        path: Path to a .evalset.json file.

    Returns:
        Deserialized EvalSet with all eval_cases populated.

    Raises:
        FileNotFoundError: If the file does not exist or a referenced local file is missing.
        ValidationError: If the file does not conform to the EvalSet schema.
    """
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Evalset file not found: {resolved}")

    raw = json.loads(resolved.read_text())
    raw = _resolve_local_files(raw, base_dir=resolved.parent)
    return EvalSet.model_validate(raw)
