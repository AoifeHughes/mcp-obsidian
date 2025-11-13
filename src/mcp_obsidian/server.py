import json
import logging
from collections.abc import Sequence
from functools import lru_cache
from typing import Any
import os
from dotenv import load_dotenv
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

load_dotenv()

from . import tools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-obsidian")

# Note: OBSIDIAN_API_KEY is validated at runtime when tools are used, not at import time
# This allows the server to start and report available tools even if config is incomplete

app = Server("mcp-obsidian")

tool_handlers = {}
def add_tool_handler(tool_class: tools.ToolHandler):
    global tool_handlers

    tool_handlers[tool_class.name] = tool_class

def get_tool_handler(name: str) -> tools.ToolHandler | None:
    if name not in tool_handlers:
        return None
    
    return tool_handlers[name]

# Core file operations
add_tool_handler(tools.ListFilesToolHandler())
add_tool_handler(tools.GetFileContentsToolHandler())

# Discovery & Search
add_tool_handler(tools.FuzzySearchToolHandler())

# File modification
add_tool_handler(tools.AppendContentToolHandler())
add_tool_handler(tools.PatchContentToolHandler())
add_tool_handler(tools.PutContentToolHandler())

# Task creation
add_tool_handler(tools.CreateSmartTaskToolHandler())

# Dataview query tools
add_tool_handler(tools.DataviewQueryToolHandler())
add_tool_handler(tools.SuggestColumnsToolHandler())
add_tool_handler(tools.GetPropertyValuesToolHandler())

# Add new content management tools
# These tools are optional - server will work without them if Keys folder doesn't exist
content_tools_loaded = 0
content_tools_failed = []

try:
    from .content_tools import GameToolHandler, BookToolHandler, GitHubToolHandler, SteamToolHandler

    # Register game tools
    try:
        game_handler = GameToolHandler()
        for tool_desc in game_handler.get_tool_descriptions():
            wrapper = tools.create_tool_handler_wrapper(tool_desc.name, game_handler)
            add_tool_handler(wrapper)
            content_tools_loaded += 1
        logger.info("✅ Game tools loaded successfully")
    except Exception as e:
        content_tools_failed.append(f"Game tools: {str(e)}")
        logger.warning(f"⚠️  Game tools not available: {e}")

    # Register book tools
    try:
        book_handler = BookToolHandler()
        for tool_desc in book_handler.get_tool_descriptions():
            wrapper = tools.create_tool_handler_wrapper(tool_desc.name, book_handler)
            add_tool_handler(wrapper)
            content_tools_loaded += 1
        logger.info("✅ Book tools loaded successfully")
    except Exception as e:
        content_tools_failed.append(f"Book tools: {str(e)}")
        logger.warning(f"⚠️  Book tools not available: {e}")

    # Register GitHub tools
    try:
        github_handler = GitHubToolHandler()
        for tool_desc in github_handler.get_tool_descriptions():
            wrapper = tools.create_tool_handler_wrapper(tool_desc.name, github_handler)
            add_tool_handler(wrapper)
            content_tools_loaded += 1
        logger.info("✅ GitHub tools loaded successfully")
    except Exception as e:
        content_tools_failed.append(f"GitHub tools: {str(e)}")
        logger.warning(f"⚠️  GitHub tools not available: {e}")

    # Register Steam tools
    try:
        steam_handler = SteamToolHandler()
        for tool_desc in steam_handler.get_tool_descriptions():
            wrapper = tools.create_tool_handler_wrapper(tool_desc.name, steam_handler)
            add_tool_handler(wrapper)
            content_tools_loaded += 1
        logger.info("✅ Steam tools loaded successfully")
    except Exception as e:
        content_tools_failed.append(f"Steam tools: {str(e)}")
        logger.warning(f"⚠️  Steam tools not available: {e}")

    if content_tools_loaded > 0:
        logger.info(f"✅ Loaded {content_tools_loaded} content management tool groups")
    if content_tools_failed:
        logger.info(f"ℹ️  Some content tools unavailable. To enable them, set up Keys/api_keys.json")

except ImportError as e:
    logger.warning(f"⚠️  Content management tools module not available: {e}")
except Exception as e:
    logger.warning(f"⚠️  Unexpected error loading content tools: {e}")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""

    return [th.get_tool_description() for th in tool_handlers.values()]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls for command line run."""
    
    if not isinstance(arguments, dict):
        raise RuntimeError("arguments must be dictionary")


    tool_handler = get_tool_handler(name)
    if not tool_handler:
        raise ValueError(f"Unknown tool: {name}")

    try:
        return tool_handler.run_tool(arguments)
    except Exception as e:
        logger.error(str(e))
        raise RuntimeError(f"Caught Exception. Error: {str(e)}")


async def main():

    # Import here to avoid issues with event loops
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )
