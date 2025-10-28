#!/usr/bin/env python3
"""Debug script to see what the API actually returns."""

import os
import sys
import json
from pathlib import Path

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

# Test a simple query
query = 'TABLE title FROM "Reading" LIMIT 2'
print(f"Query: {query}\n")

result = api.execute_dataview_query(query, format="json")
print("Raw JSON result:")
print(json.dumps(result, indent=2))
print("\nType:", type(result))

# Try with files that should exist
query2 = 'LIST FROM "Notes" WHERE file.name = "2025-10-28"'
print(f"\n\nQuery 2: {query2}\n")
result2 = api.execute_dataview_query(query2, format="json")
print("Raw JSON result 2:")
print(json.dumps(result2, indent=2))
