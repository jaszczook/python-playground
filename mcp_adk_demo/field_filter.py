"""
OpenAPI-driven response field filtering for FastMCP.

Builds a per-tool allowlist from response schemas at startup, then strips any
fields not declared in the spec before the result reaches the agent.
"""

import json

import mcp.types as mt
from fastmcp.server.middleware.middleware import Middleware, MiddlewareContext
from fastmcp.tools.base import ToolResult


def _resolve_ref(spec: dict, ref: str) -> dict:
    """Follow a JSON $ref like '#/components/schemas/Foo' within the same spec."""
    parts = ref.lstrip("#/").split("/")
    obj: dict = spec
    for part in parts:
        obj = obj[part]
    return obj


def _schema_fields(spec: dict, schema: dict) -> set[str]:
    """Return the top-level property names for a schema, resolving $ref if needed."""
    if "$ref" in schema:
        schema = _resolve_ref(spec, schema["$ref"])
    if schema.get("type") == "object":
        return set(schema.get("properties", {}).keys())
    if schema.get("type") == "array":
        items = schema.get("items", {})
        if "$ref" in items:
            items = _resolve_ref(spec, items["$ref"])
        if items.get("type") == "object":
            return set(items.get("properties", {}).keys())
    return set()


def build_response_fields(spec: dict, namespace: str) -> dict[str, set[str]]:
    """Build a mapping of MCP tool name → allowed top-level response fields.

    Only operations with a 2xx application/json schema are added; tools without
    a schema are absent from the map and pass through unfiltered.
    Tool names follow FastMCP's namespaced convention: {namespace}_{operationId}.
    """
    result: dict[str, set[str]] = {}
    for path_item in spec.get("paths", {}).values():
        for op in path_item.values():
            if not isinstance(op, dict):
                continue
            op_id = op.get("operationId")
            if not op_id:
                continue
            tool_name = f"{namespace}_{op_id}"
            for status, response in op.get("responses", {}).items():
                if not str(status).startswith("2"):
                    continue
                schema = (
                    response.get("content", {})
                    .get("application/json", {})
                    .get("schema")
                )
                if schema:
                    result[tool_name] = _schema_fields(spec, schema)
                break  # use first 2xx response
    return result


def _filter_fields(data: object, allowed: set[str]) -> object:
    if isinstance(data, dict):
        if not allowed:
            return {}
        # If the dict looks like a schema object (shares keys with allowed), filter it.
        # Otherwise treat it as a wrapper and descend into its values.
        if any(k in allowed for k in data):
            return {k: v for k, v in data.items() if k in allowed}
        return {k: _filter_fields(v, allowed) for k, v in data.items()}
    if isinstance(data, list):
        return [_filter_fields(item, allowed) for item in data]
    return data


class FieldFilterMiddleware(Middleware):
    """Strip response fields not declared in the OpenAPI spec for each operation."""

    def __init__(self, response_fields: dict[str, set[str]]) -> None:
        self._fields = response_fields

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next,
    ) -> ToolResult:
        result = await call_next(context)
        allowed = self._fields.get(context.message.name)
        if allowed is None:
            return result
        structured = result.structured_content
        if structured is not None:
            structured = _filter_fields(structured, allowed)
            filtered_content = [mt.TextContent(type="text", text=json.dumps(structured))]
        else:
            filtered_content = []
            for item in result.content:
                if isinstance(item, mt.TextContent):
                    try:
                        parsed = json.loads(item.text)
                        item = mt.TextContent(
                            type="text",
                            text=json.dumps(_filter_fields(parsed, allowed)),
                        )
                    except (json.JSONDecodeError, AttributeError):
                        pass
                filtered_content.append(item)
        return ToolResult(content=filtered_content, structured_content=structured)
