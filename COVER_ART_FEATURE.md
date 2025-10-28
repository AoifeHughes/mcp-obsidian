# Cover Art Download Feature

## Summary

Added automatic cover art download functionality to the `obsidian_add_game` tool. When adding a new game, the tool now:
1. Fetches the game's cover art from IGDB
2. Downloads it to `Attachments/game_covers/`
3. Adds the `image_url` field to the game file's frontmatter

## Why It Wasn't Working Before

When you added "Pokémon Legends: Z-A", the cover art download feature didn't exist yet in the MCP tool. The original `game_metadata_manager.py` script had this feature, but the MCP tool implementation was missing it.

## Changes Made

### 1. Added Cover Art Download Method
**File**: `src/mcp_obsidian/content_tools/game_tools.py`

Added `_download_cover_art()` method:
```python
def _download_cover_art(self, image_id: str, game_slug: str) -> Optional[str]:
    """Download cover art from IGDB and save to Attachments/game_covers."""
    # Constructs IGDB cover URL
    cover_url = f"https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg"

    # Downloads to: Attachments/game_covers/{game-slug}.jpg
    # Returns: Relative path for Obsidian
```

### 2. Updated Game Addition Flow
Modified `_add_game()` to:
- Check if game data includes cover information
- Download cover art if available
- Add `image_url` to frontmatter

```python
# Download cover art if available
if game_data.get('cover') and game_data['cover'].get('image_id'):
    cover_path = self._download_cover_art(
        game_data['cover']['image_id'],
        safe_title
    )
    if cover_path:
        frontmatter['image_url'] = cover_path
```

### 3. Added requests import
Added `import requests` for HTTP downloads.

## How It Works

1. **IGDB API** returns cover data in format:
   ```json
   {
     "cover": {
       "id": 462648,
       "image_id": "co9wzc"
     }
   }
   ```

2. **Cover URL** is constructed:
   ```
   https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg
   ```

3. **Image is downloaded** to:
   ```
   /Users/aoife/git/Obsidian/Attachments/game_covers/{game-slug}.jpg
   ```

4. **Frontmatter is updated** with:
   ```yaml
   image_url: Attachments/game_covers/{game-slug}.jpg
   ```

## Testing

### Test 1: New Game Addition
```bash
python test_game_with_cover.py
```
**Result**: ✅ Cover downloaded (23KB) for "The Legend of Zelda: Breath of the Wild"

### Test 2: Fixed Existing Game
```bash
python fix_pokemon_cover.py
```
**Result**: ✅ Cover downloaded (21KB) for "Pokémon Legends: Z-A" and file updated

## File Structure

```
Obsidian/
├── Gaming/
│   └── Games/
│       └── pokémon-legends-z-a.md  (with image_url reference)
└── Attachments/
    └── game_covers/
        └── pokémon-legends-z-a.jpg  (21KB cover image)
```

## Usage

From now on, when you add a game via MCP:

```python
# Via MCP tool
obsidian_add_game({"title": "Celeste"})

# Result:
# ✅ Creates: Gaming/Games/celeste.md
# ✅ Downloads: Attachments/game_covers/celeste.jpg
# ✅ Adds to frontmatter: image_url: Attachments/game_covers/celeste.jpg
```

## Error Handling

- Cover art download is **optional** - if it fails, the game file is still created
- Failures are logged but don't interrupt the flow
- Common reasons for failure:
  - Game has no cover art in IGDB database
  - Network issues
  - Image URL format changes

## Benefits

1. **Automatic**: No manual cover art download needed
2. **Consistent**: All covers stored in same location with predictable naming
3. **Resilient**: Failures don't block game addition
4. **Standard Format**: Uses IGDB's high-quality `t_cover_big` format

## Future Enhancements (Optional)

Potential improvements:
- Add cover art to the markdown content (not just frontmatter)
- Support custom cover art upload
- Batch download covers for existing games missing them
- Cache covers to avoid re-downloading
- Support different cover sizes/qualities

## Status

✅ **Complete** - Cover art now downloads automatically when adding games via MCP.

For the Pokémon Legends: Z-A game you added earlier, I've manually downloaded and added the cover art using the fix script.
