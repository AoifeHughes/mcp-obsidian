#!/usr/bin/env python3
"""
Example usage of the Dataview query tools.
Demonstrates common patterns for querying Obsidian vault data.
"""

import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from mcp_obsidian import obsidian

# Load configuration
keys_path = Path(__file__).parent.parent.parent / "Keys" / "api_keys.json"
with open(keys_path) as f:
    config = json.load(f)
    obsidian_config = config.get("obsidian", {})
    api_key = obsidian_config.get("api_key")
    host = obsidian_config.get("host", "127.0.0.1")
    port = obsidian_config.get("port", 27124)

# Initialize API
api = obsidian.Obsidian(api_key=api_key, host=host, port=port)

print("=" * 80)
print("Obsidian Dataview Query Examples")
print("=" * 80)

# Example 1: Discover what properties are available for books
print("\n📚 Example 1: Discover available book properties")
print("-" * 80)
properties = api.list_all_properties()
book_properties = [p for p in properties if p in [
    'title', 'author', 'reading_status', 'rating', 'publication_year',
    'genres', 'series', 'pages', 'publisher'
]]
print(f"Available book properties: {', '.join(book_properties)}")

# Example 2: Get all books with their ratings
print("\n📚 Example 2: All books with ratings")
print("-" * 80)
query = 'TABLE title, author, rating FROM "Reading/Books" WHERE rating SORT rating DESC LIMIT 5'
result = api.execute_dataview_query(query, format="markdown_table")
print(result)

# Example 3: Find high-priority tasks
print("\n✅ Example 3: High-priority in-progress tasks")
print("-" * 80)
query = '''TABLE file.link as Task, status, priority, project
FROM "Work"
WHERE status = "⚡ In-Progress" AND priority = "🔴 High"'''
result = api.execute_dataview_query(query, format="markdown_table")
print(result)

# Example 4: Games currently being played
print("\n🎮 Example 4: Currently playing games")
print("-" * 80)
query = 'TABLE game_title, platform, rating FROM "Gaming/Games" WHERE play_status = "🎮 Playing" LIMIT 5'
result = api.execute_dataview_query(query, format="markdown_table")
print(result)

# Example 5: Top-rated content across categories
print("\n⭐ Example 5: Top-rated books (5 stars)")
print("-" * 80)
query = 'TABLE title, author FROM "Reading/Books" WHERE rating = "⭐⭐⭐⭐⭐" LIMIT 3'
result = api.execute_dataview_query(query, format="markdown_table")
print(result)

# Example 6: Recent tasks (using file metadata)
print("\n📅 Example 6: Recently created tasks")
print("-" * 80)
query = 'TABLE file.link as Task, project, status, created FROM "Work" SORT created DESC LIMIT 5'
result = api.execute_dataview_query(query, format="markdown_table")
print(result)

# Example 7: JSON format for programmatic processing
print("\n💾 Example 7: JSON format output")
print("-" * 80)
query = 'TABLE title, author FROM "Reading/Books" LIMIT 2'
result = api.execute_dataview_query(query, format="json")
print("JSON output (first result):")
print(json.dumps(result[0], indent=2))

print("\n" + "=" * 80)
print("✅ Examples complete!")
print("=" * 80)
