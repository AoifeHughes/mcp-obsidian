# Game Tools Fix - Token Cache Path Issue

## Problem

The `obsidian_add_game` tool was failing with the error:
```
❌ Error adding game: [Errno 2] No such file or directory: 'Scripts/igdb_token_cache.json'
```

## Root Cause

The IGDB client was using a hardcoded relative path for its token cache file:
```python
TOKEN_CACHE_FILE = "Scripts/igdb_token_cache.json"
```

When the MCP server runs, it's not necessarily running from the vault root directory, so this relative path didn't exist and couldn't be created.

## Solution

### 1. Updated KeyManager
**File**: `src/mcp_obsidian/key_manager.py`

Added `keys_dir` property to expose the Keys directory path:
```python
self.keys_dir = self.vault_path / "Keys"
self.keys_path = self.keys_dir / "api_keys.json"
```

### 2. Updated IGDBClient
**File**: `src/mcp_obsidian/clients/igdb_client.py`

Changed token cache path to use the Keys directory:
```python
# Before (hardcoded relative path)
TOKEN_CACHE_FILE = "Scripts/igdb_token_cache.json"

# After (dynamic path in Keys directory)
keys_dir = self._key_manager.keys_dir
self.TOKEN_CACHE_FILE = keys_dir / "igdb_token_cache.json"
```

Also updated `_save_token_cache()` to ensure the directory exists:
```python
def _save_token_cache(self):
    """Save token to cache"""
    cache = {
        'token': self.token,
        'expires_at': self.token_expires_at
    }

    # Ensure Keys directory exists
    cache_path = Path(self.TOKEN_CACHE_FILE)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    with open(cache_path, 'w') as f:
        json.dump(cache, f)
```

### 3. Updated .gitignore
**File**: `Keys/.gitignore`

Added pattern to ignore token cache files:
```gitignore
# Ignore token cache files (contain temporary API tokens)
*_token_cache.json
```

## Benefits

1. **Reliable Path**: Token cache now uses an absolute path that works regardless of where the MCP server is running from
2. **Centralized Storage**: All API-related files (keys and tokens) are stored in the same `Keys/` directory
3. **Automatic Directory Creation**: The code now ensures the directory exists before writing
4. **Security**: Token cache files are properly ignored by git

## Testing

Created comprehensive test suite to verify the fix:

### Test 1: Client Initialization
```bash
python test_game_add.py
```
**Result**: ✅ Successfully initializes and stores token at correct path

### Test 2: Complete Workflow
```bash
python test_game_tools_complete.py
```
**Result**: ✅ All operations work correctly:
- Game search ✅
- Token retrieval ✅
- Game file creation ✅

### Verification

Token cache file now correctly created at:
```
/Users/aoife/git/Obsidian/Keys/igdb_token_cache.json
```

## Files Modified

1. `src/mcp_obsidian/key_manager.py` - Added `keys_dir` property
2. `src/mcp_obsidian/clients/igdb_client.py` - Fixed token cache path
3. `Keys/.gitignore` - Added token cache ignore pattern

## Usage

The fix is transparent to users. The game tools now work correctly:

```python
# Via MCP tool
result = handler.run_tool("obsidian_add_game", {
    "title": "Celeste"
})
# ✅ Works! Creates game file with full metadata
```

## Additional Notes

- Token cache files contain temporary OAuth tokens that expire (typically after a few hours)
- These tokens are automatically refreshed when they expire
- The cache improves performance by avoiding unnecessary token requests
- Token cache is ignored by git for security

## Status

✅ **Fixed and Tested** - Game addition tool now works correctly with proper token caching.
