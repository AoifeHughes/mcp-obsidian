"""
MCP Tool Handlers
"""

# Import base classes and utilities from parent tools module
import sys
from pathlib import Path

# We need to import from the sibling tools.py file, not this package
# So we'll re-export the needed items here
parent_module = __import__('mcp_obsidian.tools', fromlist=[''])

# Re-export the base ToolHandler and utilities
ToolHandler = parent_module.ToolHandler
create_tool_handler_wrapper = parent_module.create_tool_handler_wrapper

# Import our new handlers
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
