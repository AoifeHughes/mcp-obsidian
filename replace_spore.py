#!/usr/bin/env python3
"""Replace incorrect Spore game with the correct EA version."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_obsidian.content_tools.game_tools import GameToolHandler
from mcp_obsidian.clients import IGDBClient
from mcp_obsidian.key_manager import KeyManager
from mcp_obsidian import obsidian
import json

print("=" * 80)
print("Replacing Spore game")
print("=" * 80)

# Initialize
handler = GameToolHandler()
client = IGDBClient()
key_manager = KeyManager()

# Search for the correct Spore (EA game from 2008)
print("\n[1] Searching for Spore games in IGDB...")
results = client.search_games("Spore", limit=10)

print(f"Found {len(results)} results:\n")
for i, game in enumerate(results, 1):
    release_year = "Unknown"
    if game.get('first_release_date'):
        from datetime import datetime
        release_year = datetime.fromtimestamp(game['first_release_date']).year

    platforms = [p.get('name', '') for p in game.get('platforms', [])]
    print(f"{i}. {game['name']} ({release_year})")
    print(f"   Platforms: {', '.join(platforms[:3])}")
    print(f"   ID: {game['id']}")
    print()

# Find the EA Spore (2008)
ea_spore = None
for game in results:
    if game.get('first_release_date'):
        from datetime import datetime
        year = datetime.fromtimestamp(game['first_release_date']).year
        if 2008 <= year <= 2009:  # EA Spore was released in 2008
            platforms = [p.get('name', '') for p in game.get('platforms', [])]
            if any('PC' in p or 'Mac' in p for p in platforms):
                ea_spore = game
                break

if not ea_spore:
    print("❌ Could not find EA Spore. Using first result with PC platform...")
    for game in results:
        platforms = [p.get('name', '') for p in game.get('platforms', [])]
        if any('PC' in p or 'Mac' in p for p in platforms):
            ea_spore = game
            break

if ea_spore:
    print(f"[2] Selected: {ea_spore['name']} (ID: {ea_spore['id']})")

    # Delete old file and cover
    print("\n[3] Removing old Spore file and cover...")
    vault_path = key_manager.vault_path
    old_file = vault_path / "Gaming" / "Games" / "spore.md"
    old_cover = vault_path / "Attachments" / "game_covers" / "spore.jpg"

    if old_file.exists():
        old_file.unlink()
        print(f"   ✅ Deleted {old_file}")

    if old_cover.exists():
        old_cover.unlink()
        print(f"   ✅ Deleted {old_cover}")

    # Add the correct game
    print("\n[4] Adding correct Spore game...")
    result = handler.run_tool("obsidian_add_game", {
        "title": ea_spore['name'],
        "game_id": ea_spore['id']
    })

    print(result[0].text)
    print("\n✅ Replacement complete!")
else:
    print("❌ Could not find suitable Spore game")
