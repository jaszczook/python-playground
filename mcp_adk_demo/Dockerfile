# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Install uv from its official image — same tool used in local dev
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency manifests first so this layer is cached on source-only edits
COPY pyproject.toml uv.lock ./

# Install exact locked versions; skip dev extras; no lock file updates allowed
RUN uv sync --frozen --no-dev

# Copy application source after deps to preserve the cache layer above
COPY mcp_server.py field_filter.py ./
COPY examples/ ./examples/

# MCP server listens on 8080 (hardcoded in mcp_server.py __main__ block)
EXPOSE 8080

# Where mcp_server.py forwards upstream REST calls — override at runtime
ENV API_HOST=http://localhost:8000

# Start the MCP server
CMD ["uv", "run", "python", "mcp_server.py"]
