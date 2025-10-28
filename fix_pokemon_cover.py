#!/usr/bin/env python3
"""Add cover art to the existing Pokémon Legends: Z-A file."""

import sys
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_obsidian import obsidian
from mcp_obsidian.key_manager import KeyManager

# Initialize
key_manager = KeyManager()
vault_path = key_manager.vault_path

# Download cover
image_id = "co9wzc"
cover_url = f"https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg"

print(f"Downloading cover from {cover_url}...")

# Create cover directory
cover_dir = vault_path / "Attachments" / "game_covers"
cover_dir.mkdir(parents=True, exist_ok=True)

cover_path = cover_dir / "pokémon-legends-z-a.jpg"

# Download
response = requests.get(cover_url, timeout=10)
response.raise_for_status()

with open(cover_path, 'wb') as f:
    f.write(response.content)

print(f"✅ Downloaded cover: {cover_path}")
print(f"   Size: {cover_path.stat().st_size} bytes")

# Update the markdown file
api = obsidian.Obsidian(
    api_key=key_manager.get_obsidian_api_key(),
    host=key_manager.get_obsidian_host(),
    port=key_manager.get_obsidian_port()
)

filepath = "Gaming/Games/pokémon-legends-z-a.md"
content = api.get_file_contents(filepath)

# Add image_url to frontmatter
if "image_url:" not in content:
    # Find the end of frontmatter
    parts = content.split('---', 2)
    frontmatter = parts[1]
    rest = parts[2]

    # Add image_url before the closing ---
    new_frontmatter = frontmatter.rstrip() + f"\nimage_url: Attachments/game_covers/pokémon-legends-z-a.jpg\n"
    new_content = f"---{new_frontmatter}---{rest}"

    api.put_content(filepath, new_content)
    print(f"\n✅ Updated {filepath} with cover art reference")
else:
    print(f"\n⏭️  {filepath} already has image_url")

print("\n✨ Done!")
