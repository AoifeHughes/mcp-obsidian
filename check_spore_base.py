#!/usr/bin/env python3
"""Check the base Spore game details."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_obsidian.clients import IGDBClient

client = IGDBClient()

# Get the base Spore game (ID: 1876)
print("Fetching base Spore game (ID: 1876)...")
game = client.get_game_by_id(1876)

print("\nGame details:")
print(json.dumps(game, indent=2))

from datetime import datetime
if game.get('first_release_date'):
    release_date = datetime.fromtimestamp(game['first_release_date']).strftime('%Y-%m-%d')
    print(f"\n✅ This is the base Spore game released on {release_date}")

platforms = [p.get('name', '') for p in game.get('platforms', [])]
print(f"Platforms: {', '.join(platforms)}")

genres = [g.get('name', '') for g in game.get('genres', [])]
print(f"Genres: {', '.join(genres)}")

print(f"\nHas cover: {bool(game.get('cover'))}")
if game.get('cover'):
    print(f"Cover ID: {game['cover'].get('image_id')}")
