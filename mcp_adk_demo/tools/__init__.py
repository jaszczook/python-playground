from fastmcp import FastMCP


def make_tool_decorator(mcp: FastMCP, namespace: str):
    """Return a @tool decorator that auto-prefixes tool names with *namespace*.

    Supports both plain and parameterised usage:

        @tool
        async def get_status(...): ...          # → namespace_get_status

        @tool(output_schema=None)
        async def get_report(...): ...          # → namespace_get_report
    """
    def tool(fn=None, **kwargs):
        def decorator(f):
            return mcp.tool(name=f"{namespace}_{f.__name__}", **kwargs)(f)
        return decorator(fn) if fn is not None else decorator
    return tool
