# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

Uses `uv` for dependency management. Python 3.10+ required.

```bash
uv sync              # Install dependencies
uv run <script>      # Run a script in the venv
```

## Project Structure

Two independent components live in this repo:

### 1. Ragas Evaluation Pipeline

A 4-phase pipeline for evaluating ADK agents using Ragas metrics.

**Entry point:** `python run_ragas.py <evalset.json> [--threshold-* N]`

```bash
uv run python run_ragas.py ragas_eval/examples/sample.evalset.json
uv run python run_ragas.py ragas_eval/examples/sample.evalset.json --threshold-faithfulness 0.8 --threshold-factual 0.9
```

Exit codes: `0` = all metrics passed, `1` = one or more failed (useful for CI gates).

**Package:** `ragas_eval/` — all pipeline logic lives here as an importable package.

**Phase order:**
1. `ragas_eval/loader.py` — deserializes `.evalset.json` → ADK `EvalSet`
2. `ragas_eval/runner.py` — runs agent turn-by-turn in isolated sessions → `List[CaseResult]`
3. `ragas_eval/transformer.py` — maps to Ragas `SingleTurnSample` / `MultiTurnSample` schemas
4. `ragas_eval/scorer.py` — computes Faithfulness, FactualCorrectness, ToolCallAccuracy

`ragas_eval/model.py` defines `InvocationResult` (one turn) and `CaseResult` (all turns for a case).

**Note:** `run_ragas.py` imports the agent from `my_app.agent` — update this to point at the actual agent before use.

Sample evalset: `ragas_eval/examples/sample.evalset.json`

### 2. MCP + ADK Demo (`mcp_adk_demo/`)

A task management demo showing MCP ↔ ADK integration with JWT forwarding.

**Three components run independently:**

```bash
# MCP server (auto-loads specs from mcp_adk_demo/examples/*.json)
TASKS_API_BASE_URL=http://localhost:8000 USERS_API_BASE_URL=http://localhost:9000 uv run python mcp_adk_demo/mcp_server.py

# FastAPI server (proxies queries to ADK agent)
MCP_URL=http://localhost:8080/mcp uv run uvicorn mcp_adk_demo.fastapi_server:app --reload

# ADK agent (for local testing via adk web CLI)
cd mcp_adk_demo && adk web
```

**JWT flow:** Client → FastAPI (Bearer token) → stored in `session.state` → ADK runner → `header_provider` reads from session → MCP server forwards to upstream API.

`mcp_adk_demo/mcp.http` contains HTTP test requests with sequential variable capture for manual API testing.
