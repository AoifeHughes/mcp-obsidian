#!/usr/bin/env python3
"""Test game addition with cover art download."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_obsidian.content_tools.game_tools import GameToolHandler

print("=" * 80)
print("Testing Game Addition with Cover Art")
print("=" * 80)

# Initialize handler
handler = GameToolHandler()

# Test adding a game
print("\n[Test] Adding game: The Legend of Zelda: Breath of the Wild")
print("-" * 80)

result = handler.run_tool("obsidian_add_game", {
    "title": "The Legend of Zelda: Breath of the Wild"
})

print(result[0].text)

# Check if cover was downloaded
vault_path = handler._key_manager.vault_path
cover_path = vault_path / "Attachments" / "game_covers" / "the-legend-of-zelda-breath-of-the-wild.jpg"

print("\n[Verification]")
print(f"Cover art path: {cover_path}")
print(f"Cover exists: {cover_path.exists()}")

if cover_path.exists():
    print(f"✅ Cover art downloaded successfully!")
    print(f"   Size: {cover_path.stat().st_size} bytes")
else:
    print(f"❌ Cover art not found")

print("\n" + "=" * 80)
