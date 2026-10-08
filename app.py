"""Web Application Layer for Piano Music MCP.

Acts as a bridge between the browser UI and the MCP Server (server.py) using the
MCP Python SDK stdio client (ClientSession).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


def get_server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["server.py"],
        cwd=str(BASE_DIR),
    )


async def execute_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute any tool on server.py through an MCP Client stdio session."""
    server_params = get_server_params()

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            result = await session.call_tool(tool_name, arguments=arguments)
            
            for content_item in result.content:
                if hasattr(content_item, "text"):
                    try:
                        return json.loads(content_item.text)
                    except json.JSONDecodeError:
                        return {"text": content_item.text}

            return {"error": f"Empty response from tool '{tool_name}'", "status": "error"}


async def list_mcp_tools() -> list[dict[str, Any]]:
    """Query available tools from server.py via MCP tool discovery."""
    server_params = get_server_params()

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools_response = await session.list_tools()
            
            return [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                }
                for t in tools_response.tools
            ]


async def handle_index(request: Request) -> HTMLResponse:
    """Serve the main HTML interface."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Piano Music MCP UI</h1>", status_code=200)


async def handle_tools(request: Request) -> JSONResponse:
    """Return all dynamically discovered MCP tools from server.py."""
    try:
        tools = await list_mcp_tools()
        return JSONResponse({"tools": tools})
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to discover MCP tools: {str(exc)}", "status": "server_error"},
            status_code=500,
        )


async def handle_call_tool(request: Request) -> JSONResponse:
    """Call any discovered MCP tool dynamically."""
    try:
        body = await request.json()
        tool_name = body.get("tool", "").strip()
        arguments = body.get("arguments", {})
    except Exception:
        return JSONResponse({"error": "Invalid request body."}, status_code=400)

    if not tool_name:
        return JSONResponse({"error": "Tool name is required."}, status_code=400)

    try:
        data = await execute_mcp_tool(tool_name, arguments)
        return JSONResponse(data)
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to execute MCP tool '{tool_name}': {str(exc)}", "status": "server_error"},
            status_code=500,
        )


async def handle_analyze(request: Request) -> JSONResponse:
    """Backwards-compatible endpoint for chord analysis."""
    try:
        body = await request.json()
        chord = body.get("chord", "").strip()
    except Exception:
        chord = request.query_params.get("chord", "").strip()

    if not chord:
        return JSONResponse(
            {"error": "Please provide a chord name (e.g. Cmaj7, Am7, C/E).", "status": "invalid_input"},
            status_code=400,
        )

    try:
        data = await execute_mcp_tool("get_chord", {"chord": chord})
        return JSONResponse(data)
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to communicate with MCP Server: {str(exc)}", "status": "server_error"},
            status_code=500,
        )


routes = [
    Route("/", endpoint=handle_index, methods=["GET"]),
    Route("/api/tools", endpoint=handle_tools, methods=["GET"]),
    Route("/api/call-tool", endpoint=handle_call_tool, methods=["POST"]),
    Route("/api/analyze", endpoint=handle_analyze, methods=["GET", "POST"]),
    Mount("/static", app=StaticFiles(directory=str(STATIC_DIR)), name="static"),
]

app = Starlette(debug=True, routes=routes)


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("Starting Piano Music MCP Web UI on http://127.0.0.1:8000")
    print("Bridge flow: Browser -> Starlette Web Server -> MCP stdio client -> server.py")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
