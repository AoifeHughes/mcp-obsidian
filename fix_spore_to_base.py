#!/usr/bin/env python3
"""Replace Galactic Edition with base Spore game."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_obsidian.content_tools.game_tools import GameToolHandler
from mcp_obsidian.key_manager import KeyManager

print("=" * 80)
print("Replacing Spore: Galactic Edition with base Spore")
print("=" * 80)

# Initialize
handler = GameToolHandler()
key_manager = KeyManager()
vault_path = key_manager.vault_path

# Delete Galactic Edition file and cover
print("\n[1] Removing Spore: Galactic Edition...")
galactic_file = vault_path / "Gaming" / "Games" / "spore-galactic-edition.md"
galactic_cover = vault_path / "Attachments" / "game_covers" / "spore-galactic-edition.jpg"

if galactic_file.exists():
    galactic_file.unlink()
    print(f"   ✅ Deleted {galactic_file}")

if galactic_cover.exists():
    galactic_cover.unlink()
    print(f"   ✅ Deleted {galactic_cover}")

# Add base Spore game (ID: 1876)
print("\n[2] Adding base Spore game...")
result = handler.run_tool("obsidian_add_game", {
    "title": "Spore",
    "game_id": 1876
})

print(result[0].text)

# Check results
print("\n[3] Verification:")
spore_file = vault_path / "Gaming" / "Games" / "spore.md"
spore_cover = vault_path / "Attachments" / "game_covers" / "spore.jpg"

if spore_file.exists():
    print(f"   ✅ Game file created: {spore_file.name}")
else:
    print(f"   ❌ Game file not found")

if spore_cover.exists():
    print(f"   ✅ Cover downloaded: {spore_cover.name} ({spore_cover.stat().st_size} bytes)")
else:
    print(f"   ❌ Cover not found")

print("\n✅ Replacement complete!")
