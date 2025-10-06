"""
Book Tools - MCP tools for book metadata management with Calibre integration
"""

import json
import re
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from ..clients import CalibreClient
from ..key_manager import KeyManager
from .. import obsidian


class BookToolHandler:
    """Handler for book-related MCP tools"""

    def __init__(self):
        self.name = "obsidian_book_tools"
        self._key_manager = KeyManager()

        # Initialize Calibre client
        try:
            self.calibre_client = CalibreClient()
            self.calibre_available = True
        except Exception as e:
            self.calibre_available = False
            print(f"⚠️  Calibre not available: {e}")

        # Get Obsidian API config
        self.obsidian_api_key = self._key_manager.get_obsidian_api_key()
        self.obsidian_host = self._key_manager.get_obsidian_host()
        self.obsidian_port = self._key_manager.get_obsidian_port()

    def get_tool_descriptions(self) -> List[Tool]:
        """Return all book-related tool descriptions"""
        return [
            Tool(
                name="obsidian_search_books",
                description="Search for books in your Calibre library by title, author, or series name.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (title, author, or series)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 10)",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="obsidian_import_book_from_calibre",
                description="Import a book from your Calibre library into Obsidian. Creates a structured note with metadata, cover art, and reading tracking fields.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Book title to search for in Calibre"
                        },
                        "calibre_id": {
                            "type": "integer",
                            "description": "Optional: Calibre book ID if you already know it"
                        }
                    },
                    "required": ["title"]
                }
            ),
            Tool(
                name="obsidian_update_book",
                description="Update an existing book file with latest metadata from Calibre. Preserves your reading status and notes.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filepath": {
                            "type": "string",
                            "description": "Path to the book file (relative to vault root, e.g., 'Reading/Books/book-title.md')",
                            "format": "path"
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force update even if timestamps match (default: false)",
                            "default": False
                        }
                    },
                    "required": ["filepath"]
                }
            ),
            Tool(
                name="obsidian_sync_calibre",
                description="Sync multiple books from Calibre library to Obsidian. Useful for batch importing your library.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of books to sync (default: 10)",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 100
                        },
                        "skip_existing": {
                            "type": "boolean",
                            "description": "Skip books that already exist in Obsidian (default: true)",
                            "default": True
                        }
                    }
                }
            )
        ]

    def run_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Execute a book tool"""
        if not self.calibre_available:
            return [
                TextContent(
                    type="text",
                    text="❌ Calibre library not available. Please check your Calibre library path in Keys/api_keys.json"
                )
            ]

        if tool_name == "obsidian_search_books":
            return self._search_books(arguments)
        elif tool_name == "obsidian_import_book_from_calibre":
            return self._import_book(arguments)
        elif tool_name == "obsidian_update_book":
            return self._update_book(arguments)
        elif tool_name == "obsidian_sync_calibre":
            return self._sync_calibre(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _search_books(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """Search for books in Calibre"""
        query = args["query"]
        limit = args.get("limit", 10)

        try:
            results = self.calibre_client.search_books(query, limit)

            if not results:
                return [
                    TextContent(
                        type="text",
                        text=f"No books found for '{query}'"
                    )
                ]

            formatted_results = []
            for book in results:
                authors = ", ".join(book['authors'][:2])
                if len(book['authors']) > 2:
                    authors += f" (+{len(book['authors'])-2} more)"

                series_info = ""
                if book['series']:
                    series_info = f" | Series: {book['series'][0]}"
                    if book['series_index']:
                        series_info += f" #{book['series_index']}"

                pub_year = "Unknown"
                if book['pubdate']:
                    try:
                        pub_year = str(datetime.fromisoformat(
                            book['pubdate'].replace('Z', '+00:00')
                        ).year)
                    except:
                        pass

                formatted_results.append({
                    'id': book['id'],
                    'title': book['title'],
                    'authors': book['authors'],
                    'series': series_info,
                    'pub_year': pub_year,
                    'has_cover': book['has_cover']
                })

            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        'source': 'Calibre',
                        'count': len(formatted_results),
                        'results': formatted_results
                    }, indent=2)
                )
            ]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Search failed: {str(e)}"
                )
            ]

    def _import_book(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """Import a book from Calibre"""
        title = args["title"]
        calibre_id = args.get("calibre_id")

        try:
            # Get book data
            if calibre_id:
                book_data = self.calibre_client.get_book_by_id(calibre_id)
            else:
                results = self.calibre_client.search_books(title, 1)
                if not results:
                    return [
                        TextContent(
                            type="text",
                            text=f"❌ No book found for '{title}'"
                        )
                    ]
                book_data = results[0]

            # Generate filename
            safe_title = re.sub(r'[^\w\s-]', '', book_data['title']).strip()
            safe_title = re.sub(r'[-\s]+', '-', safe_title).lower()
            filepath = f"Reading/Books/{safe_title}.md"

            # Build frontmatter
            pub_date = ""
            pub_year = ""
            if book_data['pubdate']:
                try:
                    pub_dt = datetime.fromisoformat(book_data['pubdate'].replace('Z', '+00:00'))
                    pub_date = pub_dt.strftime('%Y-%m-%d')
                    pub_year = str(pub_dt.year)
                except:
                    pass

            tags = ['book', 'reading']
            if book_data['tags']:
                tags.extend([tag.lower().replace(' ', '-') for tag in book_data['tags']])

            frontmatter = {
                'title': book_data['title'],
                'author': book_data['authors'],
                'calibre_id': book_data['id'],
                'reading_status': '📖 Want to Read',
                'rating': 'Not Rated',
                'publication_date': pub_date,
                'publication_year': pub_year,
                'publisher': book_data['publishers'],
                'series': book_data['series'][0] if book_data['series'] else '',
                'series_index': book_data['series_index'],
                'languages': book_data['languages'],
                'tags': tags,
                'calibre_timestamp': book_data['timestamp']
            }

            # Build content
            import yaml
            yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)

            # Get OPF metadata for description
            opf_metadata = self.calibre_client.get_book_metadata_from_opf(book_data['path'])
            description = book_data.get('comments', 'No description available.')

            # Clean HTML from description
            if description:
                description = re.sub(r'<[^>]+>', '', description)
                description = description.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')

            series_section = ""
            if frontmatter.get('series'):
                series_section = f"\n**Series:** {frontmatter['series']}"
                if frontmatter.get('series_index'):
                    series_section += f" (Book {frontmatter['series_index']})"

            content = f"""---
{yaml_str}---

```meta-bind-embed
  [[book-button-definitions]]
```

## 📖 Book Information

**Author:** `=this.author`
**Publisher:** `=this.publisher`
**Publication Date:** `=this.publication_date`
**Languages:** `=this.languages`{series_section}

## 📝 Description

{description}

## 📊 My Reading

**Status:** `=this.reading_status`
**My Rating:** `=this.rating`

## 💭 My Thoughts

### Overall Impression

### Key Takeaways

### Favorite Quotes
>

## 📎 My Notes

## 🔗 Related Books

## 📚 Calibre Information

**Calibre ID:** {frontmatter.get('calibre_id', '')}
**Library Path:** `{book_data.get('path', '')}`
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
                    text=f"✅ Imported book: {filepath}\n\nTitle: {book_data['title']}\nAuthor(s): {', '.join(book_data['authors'])}\nCallibre ID: {book_data['id']}"
                )
            ]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error importing book: {str(e)}"
                )
            ]

    def _update_book(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """Update book metadata from Calibre"""
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

            calibre_id = frontmatter.get('calibre_id')
            if not calibre_id:
                return [
                    TextContent(
                        type="text",
                        text=f"❌ No Calibre ID found in {filepath}"
                    )
                ]

            # Get latest data from Calibre
            book_data = self.calibre_client.get_book_by_id(calibre_id)
            if not book_data:
                return [
                    TextContent(
                        type="text",
                        text=f"❌ Book ID {calibre_id} not found in Calibre"
                    )
                ]

            # Check if update needed
            if not force and frontmatter.get('calibre_timestamp') == book_data['timestamp']:
                return [
                    TextContent(
                        type="text",
                        text=f"✅ {filepath} is already up to date"
                    )
                ]

            # Update frontmatter (preserve user data)
            user_fields = ['reading_status', 'rating', 'date_started', 'date_finished']
            preserved = {k: frontmatter.get(k) for k in user_fields if k in frontmatter}

            frontmatter.update({
                'title': book_data['title'],
                'author': book_data['authors'],
                'publisher': book_data['publishers'],
                'calibre_timestamp': book_data['timestamp']
            })
            frontmatter.update(preserved)

            # Rebuild file
            yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
            new_content = f"---\n{yaml_str}---{parts[2]}"

            api.put_content(filepath, new_content)

            return [
                TextContent(
                    type="text",
                    text=f"✅ Updated book: {filepath}\n\nTitle: {book_data['title']}"
                )
            ]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error updating book: {str(e)}"
                )
            ]

    def _sync_calibre(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """Sync books from Calibre to Obsidian"""
        limit = args.get("limit", 10)
        skip_existing = args.get("skip_existing", True)

        try:
            all_books = self.calibre_client.get_all_books()[:limit]

            api = obsidian.Obsidian(
                api_key=self.obsidian_api_key,
                host=self.obsidian_host,
                port=self.obsidian_port
            )

            created = 0
            skipped = 0
            errors = 0

            for book in all_books:
                try:
                    # Generate filename
                    safe_title = re.sub(r'[^\w\s-]', '', book['title']).strip()
                    safe_title = re.sub(r'[-\s]+', '-', safe_title).lower()
                    filepath = f"Reading/Books/{safe_title}.md"

                    # Check if exists
                    if skip_existing:
                        try:
                            api.get_file_contents(filepath)
                            skipped += 1
                            continue
                        except:
                            pass

                    # Import the book
                    result = self._import_book({'calibre_id': book['id']})
                    if '✅' in result[0].text:
                        created += 1
                    else:
                        errors += 1

                except Exception as e:
                    errors += 1

            return [
                TextContent(
                    type="text",
                    text=f"📚 Calibre Sync Complete\n\nCreated: {created}\nSkipped: {skipped}\nErrors: {errors}\nTotal processed: {len(all_books)}"
                )
            ]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Sync failed: {str(e)}"
                )
            ]
