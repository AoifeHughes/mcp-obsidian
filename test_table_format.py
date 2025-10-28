#!/usr/bin/env python3
"""Test markdown table formatting."""

import json
from pathlib import Path
import sys

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

api = obsidian.Obsidian(api_key=api_key, host=host, port=port)

print("=" * 80)
print("Test 1: Simple TABLE query with markdown format")
print("=" * 80)
query = 'TABLE title, author FROM "Reading/Books" LIMIT 5'
result = api.execute_dataview_query(query, format="markdown_table")
print(result)

print("\n" + "=" * 80)
print("Test 2: Query with WHERE clause")
print("=" * 80)
query = 'TABLE title, author, reading_status FROM "Reading/Books" WHERE reading_status = "📚 Reading"'
result = api.execute_dataview_query(query, format="markdown_table")
print(result)

print("\n" + "=" * 80)
print("Test 3: Query with multiple columns")
print("=" * 80)
query = 'TABLE title, author, rating, publication_year FROM "Reading/Books" LIMIT 3'
result = api.execute_dataview_query(query, format="markdown_table")
print(result)

print("\n" + "=" * 80)
print("Test 4: Games query")
print("=" * 80)
query = 'TABLE game_title, platform, star_rating FROM "Gaming/Games" WHERE star_rating LIMIT 5'
result = api.execute_dataview_query(query, format="markdown_table")
print(result)

print("\n" + "=" * 80)
print("Test 5: Task query")
print("=" * 80)
query = 'TABLE file.link as Task, status, priority, project FROM "Work" WHERE status = "⚡ In-Progress" LIMIT 5'
result = api.execute_dataview_query(query, format="markdown_table")
print(result)
