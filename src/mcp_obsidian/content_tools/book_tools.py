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


def sanitize_tag(tag: str) -> str:
    """
    Sanitize a tag to ensure it's valid for Obsidian.

    Removes invalid characters and formats the tag properly:
    - Removes: . , ; : ! ? ' " ( ) [ ] { } / \ & @ # $ % ^ * + = < > | ` ~
    - Converts to lowercase
    - Replaces spaces with hyphens
    - Removes multiple consecutive hyphens
    - Strips leading/trailing hyphens

    Args:
        tag: Raw tag string to sanitize

    Returns:
        Sanitized tag string safe for use in Obsidian
    """
    if not tag:
        return ""

    # Remove comprehensive set of invalid characters
    # Keep only alphanumeric, spaces, and hyphens
    sanitized = re.sub(r'[.,;:!?\'"()\[\]{}\/\\&@#$%^*+=<>|`~]', '', tag)

    # Convert to lowercase
    sanitized = sanitized.lower()

    # Replace spaces with hyphens
    sanitized = sanitized.replace(' ', '-')

    # Remove multiple consecutive hyphens
    sanitized = re.sub(r'-+', '-', sanitized)

    # Strip leading/trailing hyphens
    sanitized = sanitized.strip('-')

    return sanitized


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
                description="Import a book from your Calibre library into Obsidian. Creates a structured note with metadata, cover art, and reading tracking fields. Provide either 'title' to search or 'calibre_id' for direct lookup.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Book title to search for in Calibre (optional if calibre_id is provided)"
                        },
                        "calibre_id": {
                            "type": "integer",
                            "description": "Calibre book ID for direct lookup (optional if title is provided)"
                        }
                    },
                    "required": []
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
        title = args.get("title")
        calibre_id = args.get("calibre_id")

        try:
            # Get book data - prefer calibre_id if provided
            if calibre_id:
                book_data = self.calibre_client.get_book_by_id(calibre_id)
                if not book_data:
                    return [
                        TextContent(
                            type="text",
                            text=f"❌ Book with Calibre ID {calibre_id} not found in Calibre library"
                        )
                    ]
            elif title:
                results = self.calibre_client.search_books(title, 1)
                if not results:
                    return [
                        TextContent(
                            type="text",
                            text=f"❌ No book found for '{title}'"
                        )
                    ]
                book_data = results[0]
            else:
                return [
                    TextContent(
                        type="text",
                        text="❌ Either 'title' or 'calibre_id' must be provided"
                    )
                ]

            # Generate filename
            safe_title = re.sub(r'[^\w\s-]', '', book_data['title']).strip()
            safe_title = re.sub(r'[-\s]+', '-', safe_title).lower()
            filepath = f"Reading/Books/{safe_title}.md"

            # Handle book cover
            cover_path = None
            if book_data['has_cover'] and book_data.get('path'):
                try:
                    vault_path = Path(self._key_manager.vault_path)
                    covers_dir = vault_path / "Attachments" / "book_covers"
                    cover_path = self.calibre_client.copy_cover_to_obsidian(
                        book_data['path'],
                        covers_dir,
                        safe_title
                    )
                except Exception as e:
                    print(f"⚠️  Warning: Could not copy book cover: {e}")

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

            # Build tags: base tags + sanitized Calibre tags + sanitized series name
            tags = ['book', 'reading']
            if book_data['tags']:
                tags.extend([sanitize_tag(tag) for tag in book_data['tags']])
            # Add series name as tag if present
            if book_data['series']:
                series_tag = sanitize_tag(book_data['series'][0])
                if series_tag and series_tag not in tags:
                    tags.append(series_tag)

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
                'cover': cover_path if cover_path else '',
                'formats': list(book_data['parsed_formats'].keys()) if book_data.get('parsed_formats') else [],
                'identifiers': book_data.get('parsed_identifiers', {}),
                'isbn': book_data.get('parsed_identifiers', {}).get('isbn', ''),
                'comments': book_data.get('comments', ''),
                'calibre_path': book_data.get('path', ''),
                'pages': 0,  # Not available in Calibre metadata.db
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

            cover_section = ""
            if cover_path:
                cover_section = f"""
## 📚 Cover

![[{cover_path}]]"""

            content = f"""---
{yaml_str}---

```meta-bind-embed
  [[book-button-definitions]]
```

```meta-bind-embed
  [[BookStatusButtons]]
```

## 📖 Book Information

**Author:** `=this.author`
**Publisher:** `=this.publisher`
**Publication Date:** `=this.publication_date`
**Languages:** `=this.languages`{series_section}
{cover_section}
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
            # Define fields that come from Calibre (will be overwritten)
            calibre_fields = {
                'title', 'author', 'calibre_id', 'publication_date', 'publication_year',
                'publisher', 'series', 'series_index', 'languages', 'cover',
                'calibre_timestamp', 'formats', 'identifiers', 'isbn', 'comments',
                'calibre_path', 'tags', 'pages'
            }
            # Preserve everything else (user data and custom fields)
            preserved = {k: v for k, v in frontmatter.items() if k not in calibre_fields}

            # Parse publication date
            pub_date = ""
            pub_year = ""
            if book_data['pubdate']:
                try:
                    pub_dt = datetime.fromisoformat(book_data['pubdate'].replace('Z', '+00:00'))
                    pub_date = pub_dt.strftime('%Y-%m-%d')
                    pub_year = str(pub_dt.year)
                except:
                    pass

            # Handle book cover update
            cover_path = frontmatter.get('cover', '')  # Preserve existing if present
            if book_data['has_cover'] and book_data.get('path'):
                try:
                    # Generate safe filename from title
                    safe_title = re.sub(r'[^\w\s-]', '', book_data['title']).strip()
                    safe_title = re.sub(r'[-\s]+', '-', safe_title).lower()

                    vault_path = Path(self._key_manager.vault_path)
                    covers_dir = vault_path / "Attachments" / "book_covers"
                    new_cover_path = self.calibre_client.copy_cover_to_obsidian(
                        book_data['path'],
                        covers_dir,
                        safe_title
                    )
                    if new_cover_path:
                        cover_path = new_cover_path
                except Exception as e:
                    print(f"⚠️  Warning: Could not update book cover: {e}")

            # Update all metadata fields from Calibre
            frontmatter.update({
                'title': book_data['title'],
                'author': book_data['authors'],
                'calibre_id': book_data['id'],
                'publication_date': pub_date,
                'publication_year': pub_year,
                'publisher': book_data['publishers'],
                'series': book_data['series'][0] if book_data['series'] else '',
                'series_index': book_data['series_index'],
                'languages': book_data['languages'],
                'cover': cover_path,
                'formats': list(book_data['parsed_formats'].keys()) if book_data.get('parsed_formats') else [],
                'identifiers': book_data.get('parsed_identifiers', {}),
                'isbn': book_data.get('parsed_identifiers', {}).get('isbn', ''),
                'comments': book_data.get('comments', ''),
                'calibre_path': book_data.get('path', ''),
                'pages': 0,  # Not available in Calibre metadata.db
                'calibre_timestamp': book_data['timestamp']
            })

            # Update tags: sanitize Calibre tags, add series, preserve custom tags
            existing_tags = frontmatter.get('tags', [])
            base_tags = ['book', 'reading']

            # Get sanitized Calibre tags
            calibre_tags = []
            if book_data['tags']:
                calibre_tags = [sanitize_tag(tag) for tag in book_data['tags']]

            # Get sanitized series tag
            series_tag = None
            if book_data['series']:
                series_tag = sanitize_tag(book_data['series'][0])

            # Identify custom tags (not base tags, not from Calibre, not series)
            # First, get all potential generated tags from old data
            old_calibre_tags = []
            if frontmatter.get('tags'):
                # Try to identify tags that might have been from Calibre/series
                # Keep tags that aren't 'book' or 'reading' as potential custom tags
                for tag in existing_tags:
                    if tag not in base_tags:
                        # This could be custom or from Calibre - we'll preserve it
                        old_calibre_tags.append(tag)

            # Build final tag list
            all_tags = base_tags.copy()
            all_tags.extend(calibre_tags)
            if series_tag and series_tag not in all_tags:
                all_tags.append(series_tag)

            # Add back any custom tags that weren't in the new Calibre/series tags
            # Preserve existing tags that might be custom
            for tag in existing_tags:
                if tag not in all_tags and tag not in base_tags:
                    # This is likely a custom tag - preserve it
                    all_tags.append(tag)

            # Deduplicate and sanitize all tags (including custom ones)
            all_tags = [sanitize_tag(tag) for tag in all_tags if tag]
            all_tags = list(dict.fromkeys(all_tags))  # Deduplicate while preserving order

            frontmatter['tags'] = all_tags

            # Restore preserved user fields
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

