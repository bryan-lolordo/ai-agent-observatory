"""
MCP Server for AI Agent Observatory

This is the main entry point for the MCP server. It registers all tools
and resources, handles the MCP protocol, and manages the connection
to the Observatory storage layer.

Usage:
    python -m observatory.mcp.server

Configuration via environment variables:
    OBSERVATORY_DB_URL: Database connection URL (default: sqlite:///observatory.db)
    OBSERVATORY_PROJECT: Project name for filtering data (optional)
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Any
from functools import partial

# MCP SDK imports - these will be available after installing the mcp package
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool,
        TextContent,
        Resource,
        ResourceContents,
        Prompt,
        PromptMessage,
        PromptArgument,
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("MCP SDK not installed. Run: pip install mcp", file=sys.stderr)

# Observatory imports
from observatory.mcp.tools import ALL_TOOLS, TOOL_CATEGORIES
from observatory.mcp.resources import ALL_RESOURCES, RESOURCE_CATEGORIES
from observatory.mcp.prompts import ALL_PROMPTS, PROMPT_CATEGORIES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("observatory.mcp")


class StorageAdapter:
    """
    Adapter that wraps the Observatory Storage class to provide
    the interface expected by MCP tools.

    This bridges the gap between:
    - MCP tools expecting: get_calls(since=...), get_sessions()
    - Storage providing: get_llm_calls(start_time=...), get_session(id)
    """

    def __init__(self, storage):
        self._storage = storage

    def get_calls(
        self,
        since: datetime | None = None,
        session_id: str | None = None,
        limit: int = 1000,
    ):
        """
        Get LLM calls with optional time filter.

        Maps to Storage.get_llm_calls(start_time=since)
        """
        return self._storage.get_llm_calls(
            start_time=since,
            session_id=session_id,
            limit=limit,
        )

    def get_sessions(
        self,
        since: datetime | None = None,
        active_only: bool = False,
        limit: int = 100,
    ):
        """
        Get sessions with optional filters.

        Args:
            since: Only sessions started after this time
            active_only: Only return active (not ended) sessions
            limit: Maximum sessions to return
        """
        return self._storage.get_sessions(
            start_time=since,
            active_only=active_only,
            limit=limit,
        )

    def get_session(self, session_id: str):
        """Get a single session by ID."""
        return self._storage.get_session(session_id)

    def __getattr__(self, name):
        """Forward any other method calls to the underlying storage."""
        return getattr(self._storage, name)


class ObservatoryMCPServer:
    """
    MCP Server that exposes Observatory functionality.

    Handles tool execution, resource fetching, and storage management.
    """

    def __init__(self, db_url: str | None = None, project_name: str | None = None):
        """
        Initialize the MCP server.

        Args:
            db_url: Database connection URL
            project_name: Optional project name for filtering
        """
        self.db_url = db_url or os.getenv("OBSERVATORY_DB_URL", "sqlite:///observatory.db")
        self.project_name = project_name or os.getenv("OBSERVATORY_PROJECT")
        self._storage = None
        self._server = None

    @property
    def storage(self):
        """Lazy-load storage connection with adapter."""
        if self._storage is None:
            try:
                from observatory.storage import Storage
                raw_storage = Storage(self.db_url)
                self._storage = StorageAdapter(raw_storage)
                logger.info(f"Connected to storage: {self.db_url}")
            except Exception as e:
                logger.error(f"Failed to connect to storage: {e}")
                self._storage = None
        return self._storage

    def create_server(self) -> "Server":
        """Create and configure the MCP server."""
        if not MCP_AVAILABLE:
            raise RuntimeError("MCP SDK not installed. Run: pip install mcp")

        server = Server("observatory")

        # Register tool list handler
        @server.list_tools()
        async def list_tools():
            """Return list of available tools."""
            tools = []
            for tool_def in ALL_TOOLS:
                tools.append(Tool(
                    name=tool_def.name,
                    description=tool_def.description,
                    inputSchema=tool_def.parameters,
                ))
            return tools

        # Register tool execution handler
        @server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]):
            """Execute a tool and return results."""
            # Find the tool
            tool_def = None
            for t in ALL_TOOLS:
                if t.name == name:
                    tool_def = t
                    break

            if tool_def is None:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unknown tool: {name}"})
                )]

            try:
                # Execute the tool handler with storage injected
                result = await tool_def.handler(**arguments, storage=self.storage)

                # Format result as JSON
                if isinstance(result, dict):
                    text = json.dumps(result, indent=2, default=str)
                else:
                    text = str(result)

                return [TextContent(type="text", text=text)]

            except Exception as e:
                logger.exception(f"Error executing tool {name}")
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)})
                )]

        # Register resource list handler
        @server.list_resources()
        async def list_resources():
            """Return list of available resources."""
            resources = []
            for res_def in ALL_RESOURCES:
                resources.append(Resource(
                    uri=res_def.uri,
                    name=res_def.name,
                    description=res_def.description,
                    mimeType=res_def.mime_type,
                ))
            return resources

        # Register resource read handler
        @server.read_resource()
        async def read_resource(uri: str):
            """Read a resource and return contents."""
            # Find the resource
            res_def = None
            for r in ALL_RESOURCES:
                if r.uri == uri:
                    res_def = r
                    break

            if res_def is None:
                return ResourceContents(
                    uri=uri,
                    mimeType="application/json",
                    text=json.dumps({"error": f"Unknown resource: {uri}"})
                )

            try:
                # Execute the resource handler
                if res_def.handler:
                    content = await res_def.handler(storage=self.storage)
                else:
                    content = json.dumps({"error": "Resource handler not configured"})

                return ResourceContents(
                    uri=uri,
                    mimeType=res_def.mime_type,
                    text=content,
                )

            except Exception as e:
                logger.exception(f"Error reading resource {uri}")
                return ResourceContents(
                    uri=uri,
                    mimeType="application/json",
                    text=json.dumps({"error": str(e)})
                )

        # Register prompt list handler
        @server.list_prompts()
        async def list_prompts():
            """Return list of available prompts."""
            prompts = []
            for prompt_def in ALL_PROMPTS:
                arguments = []
                if prompt_def.arguments:
                    for arg in prompt_def.arguments:
                        arguments.append(PromptArgument(
                            name=arg["name"],
                            description=arg.get("description", ""),
                            required=arg.get("required", False),
                        ))

                prompts.append(Prompt(
                    name=prompt_def.name,
                    description=prompt_def.description,
                    arguments=arguments if arguments else None,
                ))
            return prompts

        # Register prompt get handler
        @server.get_prompt()
        async def get_prompt(name: str, arguments: dict[str, str] | None = None):
            """Get a prompt template with arguments filled in."""
            # Find the prompt
            prompt_def = None
            for p in ALL_PROMPTS:
                if p.name == name:
                    prompt_def = p
                    break

            if prompt_def is None:
                return {"error": f"Unknown prompt: {name}"}

            # Fill in template with arguments
            template = prompt_def.template
            if arguments:
                for key, value in arguments.items():
                    template = template.replace(f"{{{key}}}", value)

            return {
                "messages": [
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=template),
                    )
                ]
            }

        self._server = server
        return server

    async def run(self):
        """Run the MCP server using stdio transport."""
        server = self.create_server()

        logger.info("Starting Observatory MCP Server...")
        logger.info(f"Database: {self.db_url}")
        logger.info(f"Tools registered: {len(ALL_TOOLS)}")
        logger.info(f"Resources registered: {len(ALL_RESOURCES)}")
        logger.info(f"Prompts registered: {len(ALL_PROMPTS)}")

        # Run with stdio transport
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())


def create_server(db_url: str | None = None, project_name: str | None = None) -> "Server":
    """
    Create an MCP server instance.

    Args:
        db_url: Database connection URL
        project_name: Optional project name

    Returns:
        Configured MCP Server
    """
    obs_server = ObservatoryMCPServer(db_url, project_name)
    return obs_server.create_server()


async def run_server(db_url: str | None = None, project_name: str | None = None):
    """
    Run the MCP server.

    Args:
        db_url: Database connection URL
        project_name: Optional project name
    """
    obs_server = ObservatoryMCPServer(db_url, project_name)
    await obs_server.run()


def main():
    """Main entry point."""
    if not MCP_AVAILABLE:
        print("Error: MCP SDK not installed.", file=sys.stderr)
        print("Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)

    # Get configuration from environment
    db_url = os.getenv("OBSERVATORY_DB_URL")
    project_name = os.getenv("OBSERVATORY_PROJECT")

    # Run the server
    asyncio.run(run_server(db_url, project_name))


if __name__ == "__main__":
    main()
