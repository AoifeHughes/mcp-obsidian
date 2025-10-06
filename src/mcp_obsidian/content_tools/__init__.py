"""
MCP Tool Handlers for Content Management

These handlers provide integration with external services:
- GameToolHandler: IGDB and GiantBomb for game metadata
- BookToolHandler: Calibre library integration
- GitHubToolHandler: GitHub issue import

All handlers require Keys/api_keys.json to be properly configured.
"""

# Import base classes and utilities from parent tools module
import sys
from pathlib import Path

# We need to import from the sibling tools.py file, not this package
# So we'll re-export the needed items here
try:
    parent_module = __import__('mcp_obsidian.tools', fromlist=[''])

    # Re-export the base ToolHandler and utilities
    ToolHandler = parent_module.ToolHandler
    create_tool_handler_wrapper = parent_module.create_tool_handler_wrapper
except Exception as e:
    raise ImportError(f"Failed to import base tools module: {e}")

# Import our new handlers
try:
    from .game_tools import GameToolHandler
    from .book_tools import BookToolHandler
    from .github_tools import GitHubToolHandler

    __all__ = [
        'ToolHandler',
        'create_tool_handler_wrapper',
        'GameToolHandler',
        'BookToolHandler',
        'GitHubToolHandler',
    ]
except ImportError as e:
    # This can happen if dependencies are missing
    raise ImportError(
        f"Failed to import content tool handlers. "
        f"Please ensure all dependencies are installed. Error: {e}"
    )
