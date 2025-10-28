#!/usr/bin/env python3
"""Debug Pokémon Legends: Z-A cover art data."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_obsidian.clients import IGDBClient

client = IGDBClient()

print("Searching for Pokémon Legends: Z-A...")
results = client.search_games("Pokémon Legends: Z-A", limit=1)

if results:
    game = results[0]
    print("\nGame data:")
    print(json.dumps(game, indent=2))

    print("\n\nCover data:")
    if game.get('cover'):
        print(f"✅ Cover found!")
        print(f"   Cover data: {game['cover']}")
        if game['cover'].get('image_id'):
            print(f"   Image ID: {game['cover']['image_id']}")
            print(f"   URL: https://images.igdb.com/igdb/image/upload/t_cover_big/{game['cover']['image_id']}.jpg")
        else:
            print("   ❌ No image_id in cover data")
    else:
        print("❌ No cover data in response")
else:
    print("No results found")
