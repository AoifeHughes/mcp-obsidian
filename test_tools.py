#!/usr/bin/env python3
"""
Test script to verify MCP tools are loading properly
"""
import sys
import os

# Set up environment
os.environ['OBSIDIAN_API_KEY'] = '2a3882771a1507af668c2cea302d573bb09f5a8167569dfc6443bd9b01518d75'
os.environ['OBSIDIAN_HOST'] = '127.0.0.1'
os.environ['OBSIDIAN_PORT'] = '27124'

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    print("🧪 Testing MCP Obsidian server tool loading...\n")

    # Import the server module
    from mcp_obsidian import server

    print(f"✅ Server module imported successfully")
    print(f"   Registered tools: {len(server.tool_handlers)}\n")

    # List all tools
    print("📋 Available tools:")
    print("=" * 80)

    for i, (name, handler) in enumerate(server.tool_handlers.items(), 1):
        tool_desc = handler.get_tool_description()
        print(f"{i:2d}. {tool_desc.name}")
        print(f"    {tool_desc.description[:100]}...")
        print()

    print("=" * 80)
    print(f"\n✅ Success! {len(server.tool_handlers)} tools loaded properly")

    # Check for content management tools
    content_tools = [name for name in server.tool_handlers.keys()
                     if name.startswith('obsidian_search_games')
                     or name.startswith('obsidian_add_game')
                     or name.startswith('obsidian_enrich_game')
                     or name.startswith('obsidian_search_books')
                     or name.startswith('obsidian_import_book')
                     or name.startswith('obsidian_import_github')]

    if content_tools:
        print(f"\n✅ Content management tools loaded: {len(content_tools)}")
        for tool in content_tools:
            print(f"   - {tool}")
    else:
        print("\n⚠️  No content management tools found")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
