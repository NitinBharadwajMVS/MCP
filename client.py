"""Piano Music MCP Client - Learning Layer.

Demonstrates connecting to an MCP server via stdio transport, discovering
and interacting with all three core MCP primitives:
1. Prompts   (Reusable prompt templates)
2. Resources (Static / read-only reference data)
3. Tools     (Dynamic callable actions)
"""

from __future__ import annotations

import asyncio
import json
import sys
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def run_client() -> None:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["server.py"],
    )

    print("=" * 70)
    print("Connecting to Piano Music MCP Server via stdio transport...")
    print("=" * 70)

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # 1. Initialize MCP protocol handshake
            await session.initialize()
            print("[MCP] Connection initialized successfully.\n")

            # =================================================================
            # A. MCP PROMPTS (Prompt Templates Discovery & Retrieval)
            # =================================================================
            print("=" * 70)
            print("[1. MCP PROMPTS] Discovering and Requesting Prompt Templates...")
            print("=" * 70)

            prompts_response = await session.list_prompts()
            print(f"[MCP Prompts] Discovered {len(prompts_response.prompts)} prompt(s):")
            for prompt in prompts_response.prompts:
                print(f"  • Name: {prompt.name}")
                print(f"    Description: {prompt.description}")
                if prompt.arguments:
                    args_info = [f"{a.name} ({'required' if a.required else 'optional'})" for a in prompt.arguments]
                    print(f"    Arguments: {', '.join(args_info)}")
            print()

            # Requesting and rendering the 'analyze_chord' prompt template with an argument
            prompt_name = "analyze_chord"
            prompt_args = {"chord": "Cmaj7"}
            print(f"[MCP Prompts] Requesting prompt '{prompt_name}' with arguments: {prompt_args}...")
            prompt_result = await session.get_prompt(prompt_name, arguments=prompt_args)

            print("\n[MCP Prompts] Rendered Prompt Messages:")
            print("-" * 50)
            for msg in prompt_result.messages:
                print(f"Role: [{msg.role.upper()}]")
                if hasattr(msg.content, "text"):
                    print(msg.content.text)
            print("-" * 50)
            print()

            # =================================================================
            # B. MCP RESOURCES (Read-Only Data Context)
            # =================================================================
            print("=" * 70)
            print("[2. MCP RESOURCES] Discovering and Reading Resources...")
            print("=" * 70)

            resources_response = await session.list_resources()
            print(f"[MCP Resources] Discovered {len(resources_response.resources)} resource(s):")
            for res in resources_response.resources:
                print(f"  • URI: {res.uri}")
                print(f"    Name: {res.name}")
                print(f"    MIME Type: {res.mime_type}")
                print(f"    Description: {res.description}")
            print()

            # Reading the chord formulas resource
            target_uri = "theory://chords/formulas"
            print(f"[MCP Resources] Reading resource '{target_uri}'...")
            read_result = await session.read_resource(target_uri)

            print("\n[MCP Resources] Resource Content Preview:")
            print("-" * 50)
            for content_block in read_result.contents:
                if hasattr(content_block, "text"):
                    try:
                        parsed_json = json.loads(content_block.text)
                        # Print top-level categories summary
                        print(f"Title: {parsed_json.get('title')}")
                        print(f"Categories: {list(parsed_json.get('categories', {}).keys())}")
                    except json.JSONDecodeError:
                        print(content_block.text)
            print("-" * 50)
            print()

            # =================================================================
            # C. MCP TOOLS (Dynamic Callable Functions)
            # =================================================================
            print("=" * 70)
            print("[3. MCP TOOLS] Discovering and Calling Dynamic Tools...")
            print("=" * 70)

            tools_response = await session.list_tools()
            print(f"[MCP Tools] Discovered {len(tools_response.tools)} tool(s):")
            for tool in tools_response.tools:
                print(f"  • {tool.name}: {tool.description.splitlines()[0]}")
            print()

            print("[MCP Tools] Calling tool 'get_chord' with {'chord': 'Cmaj7'}...")
            res_chord = await session.call_tool("get_chord", arguments={"chord": "Cmaj7"})
            for c in res_chord.content:
                if hasattr(c, "text"):
                    print(json.dumps(json.loads(c.text), indent=2))
            print()

            print("[MCP Tools] Calling tool 'search_music' with {'query': 'Bohemian Rhapsody', 'limit': 3}...")
            res_search = await session.call_tool("search_music", arguments={"query": "Bohemian Rhapsody", "limit": 3})
            first_recording_id = "01d2788d-862f-4d00-aa1e-f326a0d353a6"
            for c in res_search.content:
                if hasattr(c, "text"):
                    search_data = json.loads(c.text)
                    print(json.dumps(search_data, indent=2))
                    if search_data.get("results") and len(search_data["results"]) > 0:
                        first_recording_id = search_data["results"][0].get("id", first_recording_id)
            print()

            print(f"[MCP Tools] Calling tool 'get_song_details' with {{'recording_id': '{first_recording_id}'}}...")
            res_details = await session.call_tool("get_song_details", arguments={"recording_id": first_recording_id})
            for c in res_details.content:
                if hasattr(c, "text"):
                    print(json.dumps(json.loads(c.text), indent=2))

            print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_client())
