#!/usr/bin/env python3
"""Test the game addition functionality."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Test that we can initialize the IGDB client
try:
    from mcp_obsidian.clients import IGDBClient

    print("Testing IGDB client initialization...")
    client = IGDBClient()
    print(f"✅ IGDB client initialized successfully")
    print(f"   Token cache will be stored at: {client.TOKEN_CACHE_FILE}")

    # Test that we can get a token
    print("\nTesting token retrieval...")
    client._ensure_token()
    print(f"✅ Successfully obtained access token")
    print(f"   Token expires at: {client.token_expires_at}")

    # Test searching for a game
    print("\nTesting game search...")
    results = client.search_games("Minecraft", limit=1)
    if results:
        print(f"✅ Search successful!")
        print(f"   Found: {results[0].get('name')}")
    else:
        print("❌ No results found")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
