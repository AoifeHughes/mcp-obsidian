#!/usr/bin/env python3
"""
Test script for the new Dataview query tools.
This script tests the tools with various query types.
"""

import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_obsidian import obsidian

# Load configuration from Keys/api_keys.json
keys_path = Path(__file__).parent.parent.parent / "Keys" / "api_keys.json"
if keys_path.exists():
    with open(keys_path) as f:
        config = json.load(f)
        obsidian_config = config.get("obsidian", {})
        api_key = obsidian_config.get("api_key")
        host = obsidian_config.get("host", "127.0.0.1")
        port = obsidian_config.get("port", 27124)
else:
    # Fallback to environment variables
    api_key = os.getenv("OBSIDIAN_API_KEY")
    host = os.getenv("OBSIDIAN_HOST", "127.0.0.1")
    port = int(os.getenv("OBSIDIAN_PORT", "27124"))

if not api_key:
    print("ERROR: OBSIDIAN_API_KEY not set")
    print(f"Tried: {keys_path} and environment variables")
    sys.exit(1)

# Initialize API
api = obsidian.Obsidian(api_key=api_key, host=host, port=port)

print("=" * 80)
print("Testing Dataview Query Tools")
print("=" * 80)

# Test 1: Simple query - list all books
print("\n[Test 1] List all books")
print("-" * 80)
try:
    query = 'TABLE title, author FROM "Reading/Books" LIMIT 5'
    result = api.execute_dataview_query(query, format="markdown_table")
    print(result)
    print("✅ Test 1 passed")
except Exception as e:
    print(f"❌ Test 1 failed: {e}")

# Test 2: Query with WHERE clause
print("\n[Test 2] Books currently being read")
print("-" * 80)
try:
    query = 'TABLE title, author, date_started FROM "Reading/Books" WHERE reading_status = "📚 Reading"'
    result = api.execute_dataview_query(query, format="markdown_table")
    print(result)
    print("✅ Test 2 passed")
except Exception as e:
    print(f"❌ Test 2 failed: {e}")

# Test 3: Query with SORT
print("\n[Test 3] Top rated books")
print("-" * 80)
try:
    query = 'TABLE title, author, rating FROM "Reading/Books" WHERE rating SORT rating DESC LIMIT 5'
    result = api.execute_dataview_query(query, format="markdown_table")
    print(result)
    print("✅ Test 3 passed")
except Exception as e:
    print(f"❌ Test 3 failed: {e}")

# Test 4: Query games
print("\n[Test 4] Currently playing games")
print("-" * 80)
try:
    query = 'TABLE game_title, platform, star_rating FROM "Gaming/Games" WHERE play_status = "🎮 Playing" LIMIT 5'
    result = api.execute_dataview_query(query, format="markdown_table")
    print(result)
    print("✅ Test 4 passed")
except Exception as e:
    print(f"❌ Test 4 failed: {e}")

# Test 5: Query tasks with priority
print("\n[Test 5] High priority in-progress tasks")
print("-" * 80)
try:
    query = 'TABLE file.link as Task, status, priority, project FROM "Work" WHERE status = "⚡ In-Progress" AND priority = "🔴 High" LIMIT 5'
    result = api.execute_dataview_query(query, format="markdown_table")
    print(result)
    print("✅ Test 5 passed")
except Exception as e:
    print(f"❌ Test 5 failed: {e}")

# Test 6: JSON format
print("\n[Test 6] JSON format output")
print("-" * 80)
try:
    query = 'TABLE title FROM "Reading/Books" LIMIT 2'
    result = api.execute_dataview_query(query, format="json")
    print(f"Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
    print(f"Headers: {result.get('headers', 'N/A')}")
    print(f"Value count: {len(result.get('values', []))}")
    print("✅ Test 6 passed")
except Exception as e:
    print(f"❌ Test 6 failed: {e}")

# Test 7: List all properties
print("\n[Test 7] List all properties")
print("-" * 80)
try:
    properties = api.list_all_properties()
    print(f"Found {len(properties)} properties")
    print(f"Sample properties: {', '.join(properties[:10])}")
    print("✅ Test 7 passed")
except Exception as e:
    print(f"❌ Test 7 failed: {e}")

print("\n" + "=" * 80)
print("Testing Complete!")
print("=" * 80)
