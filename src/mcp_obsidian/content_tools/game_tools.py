"""
Game Tools - MCP tools for game metadata management
"""

import json
import re
import requests
import yaml
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from ..clients import IGDBClient, GiantBombClient, SteamClient
from ..key_manager import KeyManager
from .. import obsidian
from ..tag_utils import make_genre_tags


class GameToolHandler:
    """Handler for game-related MCP tools"""

    def __init__(self):
        self.name = "obsidian_game_tools"
        self._key_manager = KeyManager()
        self.igdb_client = IGDBClient()
        self.giantbomb_client = GiantBombClient()
        try:
            self.steam_client = SteamClient()
        except Exception:
            self.steam_client = None

        # Get Obsidian API config
        self.obsidian_api_key = self._key_manager.get_obsidian_api_key()
        self.obsidian_host = self._key_manager.get_obsidian_host()
        self.obsidian_port = self._key_manager.get_obsidian_port()

    def get_tool_descriptions(self) -> List[Tool]:
        """Return all game-related tool descriptions"""
        return [
            Tool(
                name="obsidian_search_games",
                description="Search for games in IGDB and GiantBomb databases. Returns game metadata including title, platforms, genres, and release dates.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Game title to search for"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 5)",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="obsidian_add_game",
                description="Create a new game file in the Obsidian vault with metadata from IGDB/GiantBomb. Downloads cover art and creates a structured note.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Game title to search for and add"
                        },
                        "game_id": {
                            "type": "integer",
                            "description": "Optional: IGDB game ID if you already know it"
                        },
                        "platform": {
                            "type": "string",
                            "description": "Optional: Preferred platform (e.g., 'PC', 'Switch', 'PS5')"
                        }
                    },
                    "required": ["title"]
                }
            ),
            Tool(
                name="obsidian_enrich_game",
                description="Update an existing game file with latest metadata from IGDB/GiantBomb. Refreshes game information while preserving user data.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filepath": {
                            "type": "string",
                            "description": "Path to the game file (relative to vault root, e.g., 'Gaming/Games/minecraft.md')",
                            "format": "path"
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force update even if already enriched (default: false)",
                            "default": False
                        }
                    },
                    "required": ["filepath"]
                }
            ),
            Tool(
                name="obsidian_search_game_matches",
                description="Search IGDB for potential matches for a game file. Use this to find the correct IGDB ID when a game has wrong metadata.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filepath": {
                            "type": "string",
                            "description": "Path to the game file (relative to vault root, e.g., 'Gaming/Games/root.md')",
                            "format": "path"
                        },
                        "search_query": {
                            "type": "string",
                            "description": "Custom search query (optional, defaults to game_title from file)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max search results to return (default: 10)",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 20
                        }
                    },
                    "required": ["filepath"]
                }
            ),
            Tool(
                name="obsidian_update_game_match",
                description="Update a game file with metadata from a specific IGDB ID. Use after searching to fix mismatched game data.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filepath": {
                            "type": "string",
                            "description": "Path to the game file (relative to vault root, e.g., 'Gaming/Games/root.md')",
                            "format": "path"
                        },
                        "igdb_id": {
                            "type": "integer",
                            "description": "IGDB game ID to use for updating the file"
                        }
                    },
                    "required": ["filepath", "igdb_id"]
                }
            )
        ]

    def run_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Execute a game tool"""
        if tool_name == "obsidian_search_games":
            return self._search_games(arguments)
        elif tool_name == "obsidian_add_game":
            return self._add_game(arguments)
        elif tool_name == "obsidian_enrich_game":
            return self._enrich_game(arguments)
        elif tool_name == "obsidian_search_game_matches":
            return self._search_game_matches(arguments)
        elif tool_name == "obsidian_update_game_match":
            return self._update_game_match(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _search_games(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """Search for games"""
        query = args["query"]
        limit = args.get("limit", 5)

        print(f"🎮 Searching for '{query}'...")

        # Search IGDB first
        try:
            results = self.igdb_client.search_games(query, limit)

            if results:
                formatted_results = []
                for i, game in enumerate(results, 1):
                    platforms = [p.get('name', '') for p in game.get('platforms', [])]
                    genres = [g.get('name', '') for g in game.get('genres', [])]

                    release_date = "Unknown"
                    if game.get('first_release_date'):
                        release_date = datetime.fromtimestamp(game['first_release_date']).strftime('%Y-%m-%d')

                    formatted_results.append({
                        'id': game.get('id'),
                        'name': game.get('name'),
                        'platforms': platforms,
                        'genres': genres,
                        'release_date': release_date,
                        'summary': game.get('summary', '')[:200] + '...' if game.get('summary') else ''
                    })

                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            'source': 'IGDB',
                            'count': len(formatted_results),
                            'results': formatted_results
                        }, indent=2)
                    )
                ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        'error': f"Search failed: {str(e)}",
                        'results': []
                    }, indent=2)
                )
            ]

    def _add_game(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """Add a new game to the vault"""
        title = args["title"]
        game_id = args.get("game_id")
        platform = args.get("platform")

        try:
            # Get game data
            if game_id:
                game_data = self.igdb_client.get_game_by_id(game_id)
            else:
                # Search and use first result
                results = self.igdb_client.search_games(title, 1)
                if not results:
                    return [
                        TextContent(
                            type="text",
                            text=f"❌ No game found for '{title}'"
                        )
                    ]
                game_data = results[0]

            # Generate filename
            safe_title = re.sub(r'[^\w\s-]', '', game_data['name']).strip()
            safe_title = re.sub(r'[-\s]+', '-', safe_title).lower()
            filepath = f"Gaming/Games/{safe_title}.md"

            # Build frontmatter
            platforms_list = [p.get('name', '') for p in game_data.get('platforms', [])]
            genres_list = [g.get('name', '') for g in game_data.get('genres', [])]

            frontmatter = {
                'game_title': game_data['name'],
                'platform': platforms_list,
                'genre': ', '.join(genres_list),
                'play_status': '🔄 Not Played',
                'rating': 'Not Rated',
                'igdb_id': game_data.get('id'),
                'tags': ['game', 'games'] + make_genre_tags(genres_list)
            }

            if game_data.get('first_release_date'):
                frontmatter['release_date'] = datetime.fromtimestamp(
                    game_data['first_release_date']
                ).strftime('%Y-%m-%d')

            # Download cover art if available
            cover_path = None
            if game_data.get('cover') and game_data['cover'].get('image_id'):
                cover_path = self._download_cover_art(
                    game_data['cover']['image_id'],
                    safe_title
                )
                if cover_path:
                    frontmatter['image_url'] = cover_path

            # Build content
            yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)

            summary = game_data.get('summary', 'No summary available.')
            cover_art_section = '\n'
            if frontmatter.get('image_url'):
                cover_art_section = '\n\n## Cover Art\n\n`= "![[" + this.image_url + "]]"`\n'

            content = f"""---
{yaml_str}---

```meta-bind-embed
  [[game-button-definitions]]
```

## Game Details
**Platform:** `=this.platform`
**Genre:** `=this.genre`
**Release Date:** `=this.release_date`
{cover_art_section}
## Description
{summary}

## My Experience
**Play Status:** `=this.play_status`
**Star Rating:** `=this.rating`

## Notes
📝

## Screenshots
"""

            # Create the file using Obsidian API
            api = obsidian.Obsidian(
                api_key=self.obsidian_api_key,
                host=self.obsidian_host,
                port=self.obsidian_port
            )

            api.put_content(filepath, content)

            return [
                TextContent(
                    type="text",
                    text=f"✅ Created game file: {filepath}\n\nGame: {game_data['name']}\nPlatforms: {', '.join(platforms_list)}\nGenres: {', '.join(genres_list)}"
                )
            ]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error adding game: {str(e)}"
                )
            ]

    def _enrich_game(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """Enrich an existing game file with metadata"""
        filepath = args["filepath"]
        force = args.get("force", False)

        try:
            # Get current file content
            api = obsidian.Obsidian(
                api_key=self.obsidian_api_key,
                host=self.obsidian_host,
                port=self.obsidian_port
            )

            content = api.get_file_contents(filepath)

            # Parse frontmatter
            if not content.startswith('---'):
                return [
                    TextContent(
                        type="text",
                        text=f"❌ File has no frontmatter: {filepath}"
                    )
                ]

            parts = content.split('---', 2)
            frontmatter = yaml.safe_load(parts[1])

            # Check if already enriched
            if not force and frontmatter.get('enriched'):
                return [
                    TextContent(
                        type="text",
                        text=f"⏭️  {filepath} already enriched (use force=true to override)"
                    )
                ]

            # Get game title
            game_title = frontmatter.get('game_title', '')
            if not game_title:
                return [
                    TextContent(
                        type="text",
                        text=f"❌ No game_title found in frontmatter"
                    )
                ]

            igdb_data = None
            if frontmatter.get('igdb_id'):
                try:
                    igdb_data = self.igdb_client.get_game_by_id(frontmatter['igdb_id'])
                except Exception as e:
                    print(f"⚠️  Could not fetch IGDB data by ID: {e}")

            if not igdb_data:
                results = self.igdb_client.search_games(game_title, 1)
                if not results:
                    return [
                        TextContent(
                            type="text",
                            text=f"❌ Game not found: {game_title}"
                        )
                    ]
                igdb_data = results[0]

            steam_appid = frontmatter.get('steam_appid')
            steam_data = None
            if steam_appid:
                steam_data = self._fetch_steam_details(steam_appid)

            self._apply_igdb_metadata(frontmatter, igdb_data)
            if steam_data:
                self._apply_steam_metadata(frontmatter, steam_data)

            safe_slug = self._slug_from_filepath(filepath)
            cover_path = frontmatter.get('image_url')
            if not cover_path:
                cover_path = self._download_cover_from_igdb(igdb_data, safe_slug)
            if not cover_path and steam_appid:
                cover_path = self._download_steam_cover(steam_appid, safe_slug)
            if cover_path:
                frontmatter['image_url'] = cover_path

            frontmatter['enriched'] = True

            # Rebuild file
            yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
            body_content = self._ensure_cover_art_section(parts[2], frontmatter.get('image_url'))
            new_content = f"---\n{yaml_str}---{body_content}"

            api.put_content(filepath, new_content)

            return [
                TextContent(
                    type="text",
                    text=f"✅ Enriched game file: {filepath}\n\nUpdated: {frontmatter.get('game_title', 'Unknown')}"
                )
            ]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error enriching game: {str(e)}"
                )
            ]

    def _slug_from_filepath(self, filepath: str) -> str:
        return Path(filepath).stem

    def _fetch_steam_details(self, appid: int) -> Optional[Dict[str, Any]]:
        if not self.steam_client:
            return None
        try:
            appid = int(appid)
        except (TypeError, ValueError):
            return None
        try:
            return self.steam_client.get_game_details(appid)
        except Exception as e:
            print(f"⚠️  Could not fetch Steam details: {e}")
            return None

    def _apply_igdb_metadata(self, frontmatter: Dict[str, Any], igdb_data: Dict[str, Any]):
        if not igdb_data:
            return

        frontmatter['game_title'] = igdb_data.get('name', frontmatter.get('game_title'))
        frontmatter['igdb_id'] = igdb_data.get('id')

        platforms = [p.get('name') for p in igdb_data.get('platforms', []) if p.get('name')]
        if platforms:
            frontmatter['platform'] = list(dict.fromkeys(platforms))

        genres = [g.get('name') for g in igdb_data.get('genres', []) if g.get('name')]
        if genres:
            frontmatter['genre'] = ', '.join(genres)

        existing_tags = frontmatter.get('tags') or []
        if not isinstance(existing_tags, list):
            existing_tags = [existing_tags]
        tags = list(dict.fromkeys(existing_tags))
        for tag in ['game', 'games'] + make_genre_tags(genres):
            if tag and tag not in tags:
                tags.append(tag)
        frontmatter['tags'] = tags

        developers = []
        publishers = []
        for company in igdb_data.get('involved_companies', []):
            company_info = company.get('company') or {}
            name = company_info.get('name')
            if not name:
                continue
            if company.get('developer'):
                developers.append(name)
            if company.get('publisher'):
                publishers.append(name)

        if developers:
            frontmatter['developer'] = ', '.join(dict.fromkeys(developers))
        if publishers:
            frontmatter['publisher'] = ', '.join(dict.fromkeys(publishers))

        themes = [t.get('name') for t in igdb_data.get('themes', []) if t.get('name')]
        if themes:
            frontmatter['themes'] = themes

        keywords = [k.get('name') for k in igdb_data.get('keywords', []) if k.get('name')]
        if keywords:
            frontmatter['keywords'] = keywords

        game_modes = [m.get('name') for m in igdb_data.get('game_modes', []) if m.get('name')]
        if game_modes:
            frontmatter['game_modes'] = game_modes

        perspectives = [p.get('name') for p in igdb_data.get('player_perspectives', []) if p.get('name')]
        if perspectives:
            frontmatter['player_perspectives'] = perspectives

        websites = [w.get('url') for w in igdb_data.get('websites', []) if w.get('url')]
        if websites:
            frontmatter['websites'] = websites

        if igdb_data.get('first_release_date'):
            frontmatter['release_date'] = datetime.fromtimestamp(
                igdb_data['first_release_date']
            ).strftime('%Y-%m-%d')

    def _apply_steam_metadata(self, frontmatter: Dict[str, Any], steam_data: Dict[str, Any]):
        if not steam_data:
            return

        if steam_data.get('developers'):
            frontmatter['developer'] = ', '.join(steam_data['developers'])

        if steam_data.get('publishers'):
            frontmatter['publisher'] = ', '.join(steam_data['publishers'])

        release_info = steam_data.get('release_date', {})
        release_date = release_info.get('date')
        if release_date:
            frontmatter.setdefault('release_date', release_date)

        platform_info = steam_data.get('platforms', {})
        if platform_info:
            platforms = [platform.title() for platform, supported in platform_info.items() if supported]
            if platforms:
                frontmatter.setdefault('platform', list(dict.fromkeys(platforms)))

        steam_genres = [g.get('description') for g in steam_data.get('genres', []) if g.get('description')]
        if steam_genres:
            frontmatter.setdefault('genre', ', '.join(steam_genres))

        existing_tags = frontmatter.get('tags') or []
        if not isinstance(existing_tags, list):
            existing_tags = [existing_tags]
        tags = list(dict.fromkeys(existing_tags))
        for tag in make_genre_tags(steam_genres):
            if tag and tag not in tags:
                tags.append(tag)
        frontmatter['tags'] = tags

    def _download_cover_from_igdb(self, igdb_data: Optional[Dict[str, Any]], slug: str, force: bool = False) -> Optional[str]:
        image_id = igdb_data.get('cover', {}).get('image_id') if igdb_data else None
        if image_id:
            return self._download_cover_art(image_id, slug, force=force)
        return None

    def _download_steam_cover(self, appid: Any, slug: str) -> Optional[str]:
        try:
            appid = int(appid)
        except (TypeError, ValueError):
            return None
        vault_path = self._key_manager.vault_path
        cover_dir = vault_path / "Attachments" / "game_covers"
        cover_dir.mkdir(parents=True, exist_ok=True)

        for suffix in ["library_600x900", "header"]:
            try:
                cover_url = f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/{suffix}.jpg"
                response = requests.get(cover_url, timeout=10)
                if response.status_code != 200:
                    continue

                cover_filename = f"{slug}-steam.jpg"
                cover_full_path = cover_dir / cover_filename
                with open(cover_full_path, 'wb') as f:
                    f.write(response.content)

                return f"Attachments/game_covers/{cover_filename}"
            except Exception as e:
                print(f"⚠️  Failed to download Steam cover ({suffix}): {e}")
                continue
        return None

    def _ensure_cover_art_section(self, body_content: str, image_url: Optional[str]) -> str:
        if not image_url or re.search(r'##\s*Cover Art', body_content, re.IGNORECASE):
            return body_content

        pattern = r'(##\s*Game Details.*?)(\n##|\Z)'
        match = re.search(pattern, body_content, re.IGNORECASE | re.DOTALL)
        cover_section = '\n\n## Cover Art\n\n`= "![[" + this.image_url + "]]"`\n'

        if match:
            insert_pos = match.end(1)
            return body_content[:insert_pos] + cover_section + body_content[insert_pos:]
        return cover_section + body_content

    def _download_cover_art(self, image_id: str, game_slug: str, force: bool = False) -> Optional[str]:
        """Download cover art from IGDB and save to Attachments/game_covers.

        Args:
            image_id: IGDB image ID
            game_slug: Safe filename slug for the game
            force: If True, download even if file already exists (overwrites)

        Returns:
            Relative path to the cover image, or None if download failed
        """
        try:
            # Determine save path
            vault_path = self._key_manager.vault_path
            cover_dir = vault_path / "Attachments" / "game_covers"
            cover_dir.mkdir(parents=True, exist_ok=True)

            cover_filename = f"{game_slug}.jpg"
            cover_full_path = cover_dir / cover_filename

            # Check if cover already exists (unless force=True)
            if not force and cover_full_path.exists():
                print(f"✓ Cover already exists: {cover_filename}")
                return f"Attachments/game_covers/{cover_filename}"

            # Construct cover URL (using t_cover_big for high quality)
            cover_url = f"https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg"

            # Download the image
            response = requests.get(cover_url, timeout=10)
            response.raise_for_status()

            # Save the image
            with open(cover_full_path, 'wb') as f:
                f.write(response.content)

            if force:
                print(f"✓ Cover updated: {cover_filename}")
            else:
                print(f"✓ Cover downloaded: {cover_filename}")

            # Return relative path for Obsidian
            return f"Attachments/game_covers/{cover_filename}"

        except Exception as e:
            # Log but don't fail - cover art is optional
            print(f"⚠️  Failed to download cover art: {e}")
            return None

    def _search_game_matches(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """Search for potential IGDB matches for a game file"""
        filepath = args["filepath"]
        search_query = args.get("search_query")
        limit = args.get("limit", 10)

        try:
            api = obsidian.Obsidian(
                api_key=self.obsidian_api_key,
                host=self.obsidian_host,
                port=self.obsidian_port
            )

            content = api.get_file_contents(filepath)

            if not content.startswith('---'):
                return [TextContent(type="text", text=f"❌ File has no frontmatter: {filepath}")]

            parts = content.split('---', 2)
            frontmatter = yaml.safe_load(parts[1])

            # Get search query
            query = search_query or frontmatter.get('game_title', '')
            if not query:
                return [TextContent(type="text", text="❌ No game title found and no search query provided")]

            results = self.igdb_client.search_games(query, limit)

            if not results:
                return [TextContent(type="text", text=f"❌ No results found for '{query}'")]

            # Format results
            formatted_results = []
            for game in results:
                platforms = [p.get('name', '') for p in game.get('platforms', [])]
                genres = [g.get('name', '') for g in game.get('genres', [])]
                release_date = "Unknown"
                if game.get('first_release_date'):
                    release_date = datetime.fromtimestamp(game['first_release_date']).strftime('%Y-%m-%d')

                formatted_results.append({
                    'id': game.get('id'),
                    'name': game.get('name'),
                    'platforms': platforms[:5],
                    'genres': genres,
                    'release_date': release_date,
                    'summary': game.get('summary', '')[:150] + '...' if game.get('summary') else ''
                })

            return [TextContent(
                type="text",
                text=json.dumps({
                    'query': query,
                    'current_title': frontmatter.get('game_title', ''),
                    'current_igdb_id': frontmatter.get('igdb_id'),
                    'count': len(formatted_results),
                    'results': formatted_results
                }, indent=2)
            )]

        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error: {str(e)}")]

    def _update_game_match(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """Update a game file with metadata from a specific IGDB ID"""
        filepath = args["filepath"]
        igdb_id = args["igdb_id"]

        try:
            api = obsidian.Obsidian(
                api_key=self.obsidian_api_key,
                host=self.obsidian_host,
                port=self.obsidian_port
            )

            content = api.get_file_contents(filepath)

            if not content.startswith('---'):
                return [TextContent(type="text", text=f"❌ File has no frontmatter: {filepath}")]

            parts = content.split('---', 2)
            frontmatter = yaml.safe_load(parts[1])

            # Get full IGDB data
            game_data = self.igdb_client.get_game_by_id(igdb_id)
            if not game_data:
                return [TextContent(type="text", text=f"❌ Could not fetch IGDB data for ID {igdb_id}")]

            # Preserve user data
            preserved_fields = ['play_status', 'rating', 'playtime', 'playtime_hours',
                               'completion_status', 'time-completed', 'steam_appid']
            preserved = {k: v for k, v in frontmatter.items() if k in preserved_fields}

            # Build new frontmatter
            new_frontmatter = {
                'game_title': game_data.get('name'),
                'igdb_id': igdb_id,
            }

            # Add metadata
            if game_data.get('platforms'):
                new_frontmatter['platform'] = [p.get('name', '') for p in game_data['platforms']]

            if game_data.get('genres'):
                genres = [g.get('name', '') for g in game_data['genres']]
                new_frontmatter['genre'] = ', '.join(genres)
                new_frontmatter['tags'] = ['game', 'games'] + make_genre_tags(genres)
            else:
                new_frontmatter['tags'] = ['game', 'games']

            if game_data.get('first_release_date'):
                new_frontmatter['release_date'] = datetime.fromtimestamp(
                    game_data['first_release_date']
                ).strftime('%Y-%m-%d')

            if game_data.get('themes'):
                new_frontmatter['themes'] = [t.get('name', '') for t in game_data['themes']]

            if game_data.get('franchises'):
                new_frontmatter['franchises'] = [f.get('name', '') for f in game_data['franchises']]

            if game_data.get('game_modes'):
                new_frontmatter['game_modes'] = [m.get('name', '') for m in game_data['game_modes']]

            if game_data.get('player_perspectives'):
                new_frontmatter['player_perspectives'] = [p.get('name', '') for p in game_data['player_perspectives']]

            if game_data.get('websites'):
                urls = [w.get('url', '') for w in game_data['websites'] if w.get('url')]
                if urls:
                    new_frontmatter['websites'] = urls[0] if len(urls) == 1 else urls

            # Add developers and publishers
            developers = []
            publishers = []
            for company in game_data.get('involved_companies', []):
                company_info = company.get('company') or {}
                name = company_info.get('name')
                if not name:
                    continue
                if company.get('developer'):
                    developers.append(name)
                if company.get('publisher'):
                    publishers.append(name)

            if developers:
                new_frontmatter['developer'] = ', '.join(dict.fromkeys(developers))
            if publishers:
                new_frontmatter['publisher'] = ', '.join(dict.fromkeys(publishers))

            # Download cover art if available (force download to replace old cover)
            safe_slug = self._slug_from_filepath(filepath)
            cover_path = self._download_cover_from_igdb(game_data, safe_slug, force=True)
            if cover_path:
                new_frontmatter['image_url'] = cover_path

            # Restore preserved user data
            new_frontmatter.update(preserved)
            new_frontmatter['enriched'] = True
            new_frontmatter['project'] = 'Games'

            # Rebuild file
            yaml_str = yaml.dump(new_frontmatter, default_flow_style=False, allow_unicode=True)
            body_content = self._ensure_cover_art_section(parts[2], new_frontmatter.get('image_url'))
            new_content = f"---\n{yaml_str}---{body_content}"

            api.put_content(filepath, new_content)

            return [TextContent(
                type="text",
                text=f"✅ Updated {filepath} with {game_data.get('name')} (IGDB ID: {igdb_id})"
            )]

        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error: {str(e)}")]
