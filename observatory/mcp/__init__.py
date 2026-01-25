"""
MCP Server for AI Agent Observatory

Exposes Observatory's observability and optimization features through
the Model Context Protocol, allowing AI assistants to query LLM metrics,
identify cost savings, and provide actionable insights.
"""

from observatory.mcp.server import create_server, run_server

__all__ = ["create_server", "run_server"]
