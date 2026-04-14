# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

Each sub-project has its own `pyproject.toml`. Uses `uv` for dependency management. Python 3.10+ required.

```bash
cd <sub-project>
uv sync              # Install dependencies
uv run <script>      # Run a script in the venv
```

## Project Structure

Three independent sub-projects live in this repo:

### 1. Ragas Evaluation Pipeline (`ragas_eval/`)

A 4-phase pipeline for evaluating ADK agents using Ragas metrics.

**Entry point:** `python run_ragas.py <evalset.json> [--threshold-* N]`

```bash
cd ragas_eval
uv run python run_ragas.py examples/sample.evalset.json
uv run python run_ragas.py examples/sample.evalset.json --threshold-faithfulness 0.8 --threshold-factual 0.9
```

Exit codes: `0` = all metrics passed, `1` = one or more failed (useful for CI gates).

**Package:** `ragas_eval/ragas_eval/` — all pipeline logic lives here as an importable package.

**Phase order:**
1. `ragas_eval/ragas_eval/loader.py` — deserializes `.evalset.json` → ADK `EvalSet`
2. `ragas_eval/ragas_eval/runner.py` — runs agent turn-by-turn in isolated sessions → `List[CaseResult]`
3. `ragas_eval/ragas_eval/transformer.py` — maps to Ragas `SingleTurnSample` / `MultiTurnSample` schemas
4. `ragas_eval/ragas_eval/scorer.py` — computes Faithfulness, FactualCorrectness, ToolCallAccuracy

`ragas_eval/ragas_eval/model.py` defines `InvocationResult` (one turn) and `CaseResult` (all turns for a case).

**Note:** `run_ragas.py` imports the agent from `my_app.agent` — update this to point at the actual agent before use.

Sample evalset: `ragas_eval/examples/sample.evalset.json`

### 2. MCP + ADK Demo (`mcp_adk_demo/`)

A task management demo showing MCP ↔ ADK integration with JWT forwarding.

**Three components run independently:**

```bash
# Mock API (Tasks + Users on a single port) — in-memory, seed data included
cd mcp_test_api
uv run python combined_app.py          # default port 8000

# MCP server (auto-loads specs from mcp_adk_demo/examples/*.json)
cd mcp_adk_demo
API_BASE_URL=http://localhost:8000 uv run python mcp_server.py
# Optional: SSL_CA_BUNDLE=<path>  (or "false" to disable TLS verification in dev)

# FastAPI server (proxies queries to ADK agent)
cd mcp_adk_demo
MCP_URL=http://localhost:8080/mcp uv run uvicorn fastapi_server:app --reload
```

**JWT flow:** Client → FastAPI (Bearer token) → stored in `session.state` → ADK runner → `header_provider` reads from session → MCP server forwards to upstream API.

`mcp_adk_demo/mcp.http` contains HTTP test requests with sequential variable capture for manual API testing.

### 3. MCP Test Agent (`mcp_test_agent/`)

ADK agent for local testing against the MCP server. Uses a hardcoded mock JWT.

```bash
# Via adk web CLI
cd mcp_test_agent && adk web

# Or run directly
cd mcp_test_agent && uv run python agent.py
```

Set `MCP_URL` to point at the running MCP server (default: `http://localhost:8080/mcp`).
