#!/usr/bin/env python3
"""
Convert MCP tool definitions to OpenAI-compatible function call format.

This script discovers all registered MCP tools and converts their schemas
to the OpenAI function calling format. The output can be used directly with
OpenAI's API.

Usage:
    python convert_to_openai_tools.py                    # Output to stdout
    python convert_to_openai_tools.py --output tools.json  # Save to file
    python convert_to_openai_tools.py --pretty             # Pretty-print JSON
    python convert_to_openai_tools.py --separate           # Create separate files per tool
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Suppress warnings during import
logging.basicConfig(level=logging.ERROR)

def convert_mcp_tool_to_openai(tool_description: Any) -> Dict[str, Any]:
    """
    Convert an MCP Tool object to OpenAI function format.

    Args:
        tool_description: MCP Tool object with name, description, and inputSchema

    Returns:
        Dictionary in OpenAI function call format
    """
    return {
        "type": "function",
        "function": {
            "name": tool_description.name,
            "description": tool_description.description,
            "parameters": tool_description.inputSchema
        }
    }

def get_all_tools() -> List[Dict[str, Any]]:
    """
    Discover and convert all registered MCP tools.

    Returns:
        List of OpenAI-formatted tool definitions
    """
    # Import server module to trigger tool registration
    from . import server

    openai_tools = []

    # Iterate through all registered tool handlers
    for tool_handler in server.tool_handlers.values():
        try:
            tool_desc = tool_handler.get_tool_description()
            openai_tool = convert_mcp_tool_to_openai(tool_desc)
            openai_tools.append(openai_tool)
        except Exception as e:
            logging.error(f"Failed to convert tool {tool_handler.name}: {e}")
            continue

    return openai_tools

def main():
    """Main entry point for the conversion script."""
    parser = argparse.ArgumentParser(
        description="Convert MCP tools to OpenAI function call format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          Output all tools to stdout (compact JSON)
  %(prog)s --pretty                 Output all tools to stdout (formatted)
  %(prog)s --output tools.json      Save all tools to a single file
  %(prog)s --separate --output-dir ./tools/  Save each tool to separate file

Note on tool execution:
  The generated JSON contains only tool schemas. To execute tools, you should
  proxy the calls back to a running MCP server instance. The MCP server handles
  all tool execution logic.
        """
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path (default: stdout)'
    )

    parser.add_argument(
        '--pretty', '-p',
        action='store_true',
        help='Pretty-print JSON with indentation'
    )

    parser.add_argument(
        '--separate', '-s',
        action='store_true',
        help='Create separate JSON file for each tool'
    )

    parser.add_argument(
        '--output-dir', '-d',
        type=str,
        default='.',
        help='Output directory for separate tool files (default: current directory)'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.separate and not args.output and args.output_dir == '.':
        print("Warning: Using --separate without --output-dir will create files in current directory",
              file=sys.stderr)

    if args.separate and args.output:
        print("Error: Cannot use both --separate and --output together", file=sys.stderr)
        print("Use --separate with --output-dir to specify where separate files should go", file=sys.stderr)
        sys.exit(1)

    # Get all tools
    try:
        openai_tools = get_all_tools()
    except Exception as e:
        print(f"Error: Failed to load tools: {e}", file=sys.stderr)
        sys.exit(1)

    if not openai_tools:
        print("Error: No tools found", file=sys.stderr)
        sys.exit(1)

    print(f"Successfully converted {len(openai_tools)} tools", file=sys.stderr)

    # Determine JSON formatting
    json_kwargs = {
        'indent': 2 if args.pretty else None,
        'ensure_ascii': False
    }

    # Output based on mode
    if args.separate:
        # Create separate files for each tool
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for tool in openai_tools:
            tool_name = tool['function']['name']
            output_file = output_dir / f"{tool_name}.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(tool, f, **json_kwargs)

            print(f"Created: {output_file}", file=sys.stderr)

        print(f"\nAll tool definitions saved to {output_dir}/", file=sys.stderr)

    else:
        # Create single output with all tools
        output_data = {
            "tools": openai_tools
        }

        json_output = json.dumps(output_data, **json_kwargs)

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_output)

            print(f"\nTool definitions saved to {output_path}", file=sys.stderr)
        else:
            # Output to stdout
            print(json_output)

if __name__ == '__main__':
    main()
