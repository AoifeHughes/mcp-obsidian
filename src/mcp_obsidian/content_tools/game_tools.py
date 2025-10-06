"""
Game Tools - MCP tools for game metadata management
"""

import json
import re
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from ..clients import IGDBClient, GiantBombClient
from ..key_manager import KeyManager
from .. import obsidian


class GameToolHandler:
    """Handler for game-related MCP tools"""

    def __init__(self):
        self.name = "obsidian_game_tools"
        self._key_manager = KeyManager()
        self.igdb_client = IGDBClient()
        self.giantbomb_client = GiantBombClient()

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
                'star_rating': 'Not Rated',
                'igdb_id': game_data.get('id'),
                'tags': ['game', 'games'] + [f"genre/{g.lower().replace(' ', '-')}" for g in genres_list]
            }

            if game_data.get('first_release_date'):
                frontmatter['release_date'] = datetime.fromtimestamp(
                    game_data['first_release_date']
                ).strftime('%Y-%m-%d')

            # Build content
            import yaml
            yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)

            summary = game_data.get('summary', 'No summary available.')

            content = f"""---
{yaml_str}---

```meta-bind-embed
  [[game-button-definitions]]
```

## Game Details
**Platform:** `=this.platform`
**Genre:** `=this.genre`
**Release Date:** `=this.release_date`

## Description
{summary}

## My Experience
**Play Status:** `=this.play_status`
**Star Rating:** `=this.star_rating`

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

            import yaml
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

            # Search for updated metadata
            results = self.igdb_client.search_games(game_title, 1)
            if not results:
                return [
                    TextContent(
                        type="text",
                        text=f"❌ Game not found: {game_title}"
                    )
                ]

            game_data = results[0]

            # Update frontmatter (preserve user data)
            platforms_list = [p.get('name', '') for p in game_data.get('platforms', [])]
            genres_list = [g.get('name', '') for g in game_data.get('genres', [])]

            frontmatter.update({
                'game_title': game_data['name'],
                'platform': platforms_list,
                'genre': ', '.join(genres_list),
                'igdb_id': game_data.get('id'),
                'enriched': True
            })

            if game_data.get('first_release_date'):
                frontmatter['release_date'] = datetime.fromtimestamp(
                    game_data['first_release_date']
                ).strftime('%Y-%m-%d')

            # Rebuild file
            yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
            new_content = f"---\n{yaml_str}---{parts[2]}"

            api.put_content(filepath, new_content)

            return [
                TextContent(
                    type="text",
                    text=f"✅ Enriched game file: {filepath}\n\nUpdated: {game_data['name']}"
                )
            ]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error enriching game: {str(e)}"
                )
            ]
