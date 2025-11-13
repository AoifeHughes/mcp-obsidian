"""
Steam Tools - MCP tools for Steam library management
"""

import json
import re
import requests
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from ..clients import SteamClient, IGDBClient
from ..key_manager import KeyManager
from .. import obsidian
from ..tag_utils import make_genre_tags


class SteamToolHandler:
    """Handler for Steam-related MCP tools"""

    def __init__(self):
        self.name = "obsidian_steam_tools"
        self._key_manager = KeyManager()
        self.steam_client = SteamClient()
        self.igdb_client = IGDBClient()  # For enriching game data

        # Get Obsidian API config
        self.obsidian_api_key = self._key_manager.get_obsidian_api_key()
        self.obsidian_host = self._key_manager.get_obsidian_host()
        self.obsidian_port = self._key_manager.get_obsidian_port()

    def get_tool_descriptions(self) -> List[Tool]:
        """Return all Steam-related tool descriptions"""
        return [
            Tool(
                name="obsidian_list_steam_games",
                description="Get a list of games from your Steam library. Returns game titles, playtime, and app IDs.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "Filter games: 'all' (default), 'played' (>0 hours), or 'unplayed'",
                            "enum": ["all", "played", "unplayed"],
                            "default": "all"
                        },
                        "sort_by": {
                            "type": "string",
                            "description": "Sort games by: 'name', 'playtime' (default), or 'recent'",
                            "enum": ["name", "playtime", "recent"],
                            "default": "playtime"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of games to return (default: 50)",
                            "default": 50,
                            "minimum": 1,
                            "maximum": 500
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="obsidian_import_steam_game",
                description="Import a game from your Steam library to Obsidian. Creates a game note with metadata, cover art, and playtime stats.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "appid": {
                            "type": "integer",
                            "description": "Steam App ID of the game to import"
                        },
                        "enrich_with_igdb": {
                            "type": "boolean",
                            "description": "Enrich Steam data with additional metadata from IGDB (default: true)",
                            "default": True
                        }
                    },
                    "required": ["appid"]
                }
            ),
            Tool(
                name="obsidian_sync_steam_library",
                description="Sync your entire Steam library (or filtered subset) to Obsidian. Creates game notes for games not already in vault.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "Import filter: 'all', 'played' (>0 hours), or 'unplayed'",
                            "enum": ["all", "played", "unplayed"],
                            "default": "played"
                        },
                        "min_playtime_hours": {
                            "type": "number",
                            "description": "Only import games with at least this many hours played (default: 0)",
                            "default": 0,
                            "minimum": 0
                        },
                        "max_games": {
                            "type": "integer",
                            "description": "Maximum number of games to import in this batch (default: 20)",
                            "default": 20,
                            "minimum": 1,
                            "maximum": 100
                        },
                        "dry_run": {
                            "type": "boolean",
                            "description": "Preview what would be imported without creating files (default: false)",
                            "default": False
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="obsidian_get_steam_stats",
                description="Get statistics about your Steam library: total games, playtime, most played, etc.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]

    def run_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Execute a Steam tool"""
        if tool_name == "obsidian_list_steam_games":
            return self._list_steam_games(arguments)
        elif tool_name == "obsidian_import_steam_game":
            return self._import_steam_game(arguments)
        elif tool_name == "obsidian_sync_steam_library":
            return self._sync_steam_library(arguments)
        elif tool_name == "obsidian_get_steam_stats":
            return self._get_steam_stats(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _list_steam_games(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """List games from Steam library"""
        filter_type = args.get("filter", "all")
        sort_by = args.get("sort_by", "playtime")
        limit = args.get("limit", 50)

        try:
            games = self.steam_client.get_owned_games()

            # Apply filters
            if filter_type == "played":
                games = [g for g in games if g.get('playtime_forever', 0) > 0]
            elif filter_type == "unplayed":
                games = [g for g in games if g.get('playtime_forever', 0) == 0]

            # Sort
            if sort_by == "name":
                games = sorted(games, key=lambda x: x.get('name', '').lower())
            elif sort_by == "playtime":
                games = sorted(games, key=lambda x: x.get('playtime_forever', 0), reverse=True)
            elif sort_by == "recent":
                games = sorted(games, key=lambda x: x.get('rtime_last_played', 0), reverse=True)

            # Limit
            games = games[:limit]

            # Format results
            formatted_games = []
            for game in games:
                playtime_hours = game.get('playtime_forever', 0) / 60
                last_played = game.get('rtime_last_played', 0)
                last_played_str = datetime.fromtimestamp(last_played).strftime('%Y-%m-%d') if last_played > 0 else 'Never'

                formatted_games.append({
                    'appid': game.get('appid'),
                    'name': game.get('name'),
                    'playtime_hours': round(playtime_hours, 1),
                    'last_played': last_played_str
                })

            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        'total_games': len(games),
                        'filter': filter_type,
                        'sort_by': sort_by,
                        'games': formatted_games
                    }, indent=2)
                )
            ]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error listing Steam games: {str(e)}"
                )
            ]

    def _import_steam_game(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """Import a single game from Steam to Obsidian"""
        appid = args["appid"]
        enrich_with_igdb = args.get("enrich_with_igdb", True)

        try:
            # Get game from Steam library
            games = self.steam_client.get_owned_games()
            steam_game = next((g for g in games if g.get('appid') == appid), None)

            if not steam_game:
                return [
                    TextContent(
                        type="text",
                        text=f"❌ Game with AppID {appid} not found in your Steam library"
                    )
                ]

            game_name = steam_game.get('name')
            playtime_hours = steam_game.get('playtime_forever', 0) / 60

            # Get detailed info from Steam Store API
            steam_details = self.steam_client.get_game_details(appid)

            # Generate filename
            safe_title = re.sub(r'[^\w\s-]', '', game_name).strip()
            safe_title = re.sub(r'[-\s]+', '-', safe_title).lower()
            filepath = f"Gaming/Games/{safe_title}.md"

            # Check if file already exists
            api = obsidian.Obsidian(
                api_key=self.obsidian_api_key,
                host=self.obsidian_host,
                port=self.obsidian_port
            )

            try:
                existing_content = api.get_file_contents(filepath)
                return [
                    TextContent(
                        type="text",
                        text=f"⏭️  Game already exists: {filepath}\nUse enrich_game tool to update it."
                    )
                ]
            except:
                pass  # File doesn't exist, continue with creation

            # Build frontmatter
            frontmatter = {
                'game_title': game_name,
                'platform': ['PC', 'Steam'],
                'play_status': '✅ Played' if playtime_hours > 0 else '🔄 Not Played',
                'rating': 'Not Rated',
                'steam_appid': appid,
                'playtime_hours': round(playtime_hours, 1),
                'tags': ['game', 'games', 'steam']
            }

            # Add Steam details if available
            if steam_details:
                if steam_details.get('genres'):
                    genres = [g.get('description', '') for g in steam_details.get('genres', [])]
                    frontmatter['genre'] = ', '.join(genres)
                    frontmatter['tags'].extend(make_genre_tags(genres))

                if steam_details.get('release_date', {}).get('date'):
                    frontmatter['release_date'] = steam_details['release_date']['date']

                if steam_details.get('developers'):
                    frontmatter['developer'] = ', '.join(steam_details['developers'])

            # Try to enrich with IGDB data
            if enrich_with_igdb:
                try:
                    igdb_results = self.igdb_client.search_games(game_name, 1)
                    if igdb_results:
                        igdb_game = igdb_results[0]

                        # Add IGDB ID
                        frontmatter['igdb_id'] = igdb_game.get('id')

                        # Get full game details for more metadata
                        full_igdb_data = self.igdb_client.get_game_by_id(igdb_game.get('id'))
                        if full_igdb_data:
                            # Add themes
                            if full_igdb_data.get('themes'):
                                themes = [t.get('name', '') for t in full_igdb_data['themes']]
                                frontmatter['themes'] = themes

                            # Add franchises
                            if full_igdb_data.get('franchises'):
                                franchises = [f.get('name', '') for f in full_igdb_data.get('franchises', [])]
                                frontmatter['franchises'] = franchises

                            # Add game modes
                            if full_igdb_data.get('game_modes'):
                                game_modes = [m.get('name', '') for m in full_igdb_data['game_modes']]
                                frontmatter['game_modes'] = game_modes

                            # Add player perspectives
                            if full_igdb_data.get('player_perspectives'):
                                perspectives = [p.get('name', '') for p in full_igdb_data['player_perspectives']]
                                frontmatter['player_perspectives'] = perspectives

                            # Add websites
                            if full_igdb_data.get('websites'):
                                urls = [w.get('url', '') for w in full_igdb_data['websites'] if w.get('url')]
                                if urls:
                                    frontmatter['websites'] = urls[0] if len(urls) == 1 else urls

                            # Enhance genres with IGDB data (more comprehensive than Steam)
                            if full_igdb_data.get('genres'):
                                igdb_genres = [g.get('name', '') for g in full_igdb_data['genres']]
                                frontmatter['genre'] = ', '.join(igdb_genres)
                                # Replace Steam genre tags with IGDB ones (more accurate)
                                frontmatter['tags'] = ['game', 'games', 'steam'] + make_genre_tags(igdb_genres)

                        # Download IGDB cover art (higher quality)
                        if igdb_game.get('cover') and igdb_game['cover'].get('image_id'):
                            cover_path = self._download_cover_art(
                                igdb_game['cover']['image_id'],
                                safe_title,
                                source='igdb'
                            )
                            if cover_path:
                                frontmatter['image_url'] = cover_path
                except Exception as e:
                    print(f"⚠️  Could not enrich with IGDB: {e}")

            # If no IGDB cover, download Steam header
            if 'image_url' not in frontmatter:
                steam_cover_path = self._download_steam_header(appid, safe_title)
                if steam_cover_path:
                    frontmatter['image_url'] = steam_cover_path

            # Build content
            import yaml
            yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)

            description = steam_details.get('short_description', 'No description available.') if steam_details else 'No description available.'
            cover_art_section = '\n'
            if frontmatter.get('image_url'):
                cover_art_section = '\n\n## Cover Art\n`= "![[" + this.image_url + "]]"`\n'

            content = f"""---
{yaml_str}---

```meta-bind-embed
  [[game-button-definitions]]
```

## Game Details
**Platform:** `=this.platform`
**Genre:** `=this.genre`
**Release Date:** `=this.release_date`
**Developer:** `=this.developer`
{cover_art_section}

## Description
{description}

## My Experience
**Play Status:** `=this.play_status`
**Star Rating:** `=this.rating`
**Playtime:** `=this.playtime_hours` hours

## Notes
📝

## Screenshots
"""

            # Create the file
            api.put_content(filepath, content)

            return [
                TextContent(
                    type="text",
                    text=f"✅ Imported Steam game: {filepath}\n\nGame: {game_name}\nPlaytime: {playtime_hours:.1f}h\nAppID: {appid}"
                )
            ]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error importing game: {str(e)}"
                )
            ]

    def _sync_steam_library(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """Sync Steam library to Obsidian"""
        filter_type = args.get("filter", "played")
        min_playtime = args.get("min_playtime_hours", 0) * 60  # Convert to minutes
        max_games = args.get("max_games", 20)
        dry_run = args.get("dry_run", False)

        try:
            # Get games from Steam
            games = self.steam_client.get_owned_games()

            # Apply filters
            if filter_type == "played":
                games = [g for g in games if g.get('playtime_forever', 0) > 0]
            elif filter_type == "unplayed":
                games = [g for g in games if g.get('playtime_forever', 0) == 0]

            # Apply playtime filter
            if min_playtime > 0:
                games = [g for g in games if g.get('playtime_forever', 0) >= min_playtime]

            # Sort by playtime descending
            games = sorted(games, key=lambda x: x.get('playtime_forever', 0), reverse=True)

            # Check which games already exist in vault
            api = obsidian.Obsidian(
                api_key=self.obsidian_api_key,
                host=self.obsidian_host,
                port=self.obsidian_port
            )

            games_to_import = []
            for game in games[:max_games]:
                game_name = game.get('name')
                safe_title = re.sub(r'[^\w\s-]', '', game_name).strip()
                safe_title = re.sub(r'[-\s]+', '-', safe_title).lower()
                filepath = f"Gaming/Games/{safe_title}.md"

                try:
                    api.get_file_contents(filepath)
                    # File exists, skip
                except:
                    # File doesn't exist, add to import list
                    games_to_import.append(game)

            if dry_run:
                preview = []
                for game in games_to_import[:max_games]:
                    playtime_hours = game.get('playtime_forever', 0) / 60
                    preview.append({
                        'appid': game.get('appid'),
                        'name': game.get('name'),
                        'playtime_hours': round(playtime_hours, 1)
                    })

                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            'dry_run': True,
                            'total_candidates': len(games),
                            'games_to_import': len(games_to_import),
                            'preview': preview[:10]
                        }, indent=2)
                    )
                ]

            # Import games
            imported = []
            errors = []

            for game in games_to_import[:max_games]:
                try:
                    result = self._import_steam_game({
                        'appid': game.get('appid'),
                        'enrich_with_igdb': True
                    })
                    imported.append(game.get('name'))
                except Exception as e:
                    errors.append(f"{game.get('name')}: {str(e)}")

            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        'imported_count': len(imported),
                        'error_count': len(errors),
                        'imported_games': imported,
                        'errors': errors
                    }, indent=2)
                )
            ]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error syncing Steam library: {str(e)}"
                )
            ]

    def _get_steam_stats(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """Get Steam library statistics"""
        try:
            games = self.steam_client.get_owned_games()

            total_games = len(games)
            played_games = [g for g in games if g.get('playtime_forever', 0) > 0]
            total_playtime = sum(g.get('playtime_forever', 0) for g in games) / 60

            # Top 10 most played
            top_games = sorted(games, key=lambda x: x.get('playtime_forever', 0), reverse=True)[:10]
            top_games_formatted = [
                {
                    'name': g.get('name'),
                    'playtime_hours': round(g.get('playtime_forever', 0) / 60, 1)
                }
                for g in top_games
            ]

            # Recently played
            recent_games = self.steam_client.get_recently_played_games(5)
            recent_formatted = [
                {
                    'name': g.get('name'),
                    'playtime_hours': round(g.get('playtime_forever', 0) / 60, 1)
                }
                for g in recent_games
            ]

            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        'total_games': total_games,
                        'played_games': len(played_games),
                        'unplayed_games': total_games - len(played_games),
                        'total_playtime_hours': round(total_playtime, 1),
                        'top_10_games': top_games_formatted,
                        'recently_played': recent_formatted
                    }, indent=2)
                )
            ]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error getting Steam stats: {str(e)}"
                )
            ]

    def _download_cover_art(self, image_id: str, game_slug: str, source: str = 'igdb') -> Optional[str]:
        """Download cover art from IGDB and save to Attachments/game_covers"""
        try:
            cover_url = f"https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg"

            vault_path = self._key_manager.vault_path
            cover_dir = vault_path / "Attachments" / "game_covers"
            cover_dir.mkdir(parents=True, exist_ok=True)

            cover_filename = f"{game_slug}.jpg"
            cover_full_path = cover_dir / cover_filename

            response = requests.get(cover_url, timeout=10)
            response.raise_for_status()

            with open(cover_full_path, 'wb') as f:
                f.write(response.content)

            return f"Attachments/game_covers/{cover_filename}"

        except Exception as e:
            print(f"⚠️  Failed to download cover art: {e}")
            return None

    def _download_steam_header(self, appid: int, game_slug: str) -> Optional[str]:
        """Download Steam header image and save to Attachments/game_covers"""
        try:
            # Try library image first (higher quality)
            cover_url = self.steam_client.get_library_image_url(appid)

            vault_path = self._key_manager.vault_path
            cover_dir = vault_path / "Attachments" / "game_covers"
            cover_dir.mkdir(parents=True, exist_ok=True)

            cover_filename = f"{game_slug}-steam.jpg"
            cover_full_path = cover_dir / cover_filename

            response = requests.get(cover_url, timeout=10)

            # If library image fails, try header image
            if response.status_code != 200:
                cover_url = self.steam_client.get_header_image_url(appid)
                response = requests.get(cover_url, timeout=10)

            response.raise_for_status()

            with open(cover_full_path, 'wb') as f:
                f.write(response.content)

            return f"Attachments/game_covers/{cover_filename}"

        except Exception as e:
            print(f"⚠️  Failed to download Steam header: {e}")
            return None
