from collections import Counter
from collections.abc import Sequence
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
import json
import os
from typing import Any

from . import obsidian

# Obsidian configuration - will be validated when tools are actually used
def get_obsidian_config():
    """Get Obsidian API configuration from environment variables"""
    api_key = os.getenv("OBSIDIAN_API_KEY", "")
    if api_key == "":
        raise ValueError(
            f"OBSIDIAN_API_KEY environment variable required. "
            f"Please set it in your MCP configuration. Working directory: {os.getcwd()}"
        )
    host = os.getenv("OBSIDIAN_HOST", "127.0.0.1")
    port = int(os.getenv("OBSIDIAN_PORT", "27124"))
    return api_key, host, port

class ToolHandler():
    def __init__(self, tool_name: str):
        self.name = tool_name

    def get_tool_description(self) -> Tool:
        raise NotImplementedError()

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        raise NotImplementedError()


def create_tool_handler_wrapper(tool_name: str, parent_handler):
    """Create a ToolHandler wrapper for multi-tool handlers"""
    class ToolHandlerWrapper(ToolHandler):
        def __init__(self):
            super().__init__(tool_name)
            self.parent = parent_handler
            # Find the matching tool description
            self.tool_desc = next(
                (t for t in parent_handler.get_tool_descriptions() if t.name == tool_name),
                None
            )

        def get_tool_description(self) -> Tool:
            return self.tool_desc

        def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
            return self.parent.run_tool(tool_name, args)

    return ToolHandlerWrapper()
    
class ListFilesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_list_files")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "List files/directories in vault. "
                "For complex filtering by properties/content, use obsidian_dataview_query instead. "
                "For fuzzy filename search, use obsidian_fuzzy_search with search_type='files'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path relative to vault root (optional, empty = vault root)",
                        "default": ""
                    },
                },
                "required": []
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        api_key, host, port = get_obsidian_config()
        api = obsidian.Obsidian(api_key=api_key, host=host, port=port)

        # Use path parameter to determine which method to call
        path = args.get("path", "")

        if path == "" or path is None:
            files = api.list_files_in_vault()
        else:
            files = api.list_files_in_dir(path)

        return [
            TextContent(
                type="text",
                text=json.dumps(files, indent=2, ensure_ascii=False)
            )
        ]
    
class GetFileContentsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_file_contents")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Read file content(s) with optional metadata. "
                "Accepts a single file path string or array of paths. "
                "Use include_metadata=true to get frontmatter, tags, and file stats along with content. "
                "Multiple files are concatenated with headers."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "oneOf": [
                            {
                                "type": "string",
                                "description": "Single file path relative to vault root"
                            },
                            {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Array of file paths relative to vault root"
                            }
                        ],
                        "description": "File path(s) to read"
                    },
                    "include_metadata": {
                        "type": "boolean",
                        "description": "Include frontmatter, tags, and file statistics (default: false)",
                        "default": False
                    }
                },
                "required": ["filepath"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "filepath" not in args:
            raise RuntimeError("filepath argument missing in arguments")

        api_key, host, port = get_obsidian_config()
        api = obsidian.Obsidian(api_key=api_key, host=host, port=port)

        filepath = args["filepath"]
        include_metadata = args.get("include_metadata", False)

        # Handle both string and array inputs
        if isinstance(filepath, list):
            # Multiple files
            if include_metadata:
                # Get both content and metadata for each file
                results = []
                for fp in filepath:
                    try:
                        content = api.get_file_contents(fp)
                        metadata = api.get_file_metadata(fp)
                        results.append({
                            "filepath": fp,
                            "content": content,
                            "metadata": metadata
                        })
                    except Exception as e:
                        results.append({
                            "filepath": fp,
                            "error": str(e)
                        })
                content = json.dumps(results, indent=2, ensure_ascii=False)
            else:
                # Just content
                content = api.get_batch_file_contents(filepath)
        else:
            # Single file
            if include_metadata:
                file_content = api.get_file_contents(filepath)
                metadata = api.get_file_metadata(filepath)
                result = {
                    "filepath": filepath,
                    "content": file_content,
                    "metadata": metadata
                }
                content = json.dumps(result, indent=2, ensure_ascii=False)
            else:
                content = api.get_file_contents(filepath)
                content = json.dumps(content, indent=2, ensure_ascii=False)

        return [
            TextContent(
                type="text",
                text=content
            )
        ]

class AppendContentToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_append_content")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Append content to a new or existing file in the vault.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the file (relative to vault root)",
                       "format": "path"
                   },
                   "content": {
                       "type": "string",
                       "description": "Content to append to the file"
                   }
               },
               "required": ["filepath", "content"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "filepath" not in args or "content" not in args:
           raise RuntimeError("filepath and content arguments required")

       api_key, host, port = get_obsidian_config()
       api = obsidian.Obsidian(api_key=api_key, host=host, port=port)
       api.append_content(args.get("filepath", ""), args["content"])

       return [
           TextContent(
               type="text",
               text=f"Successfully appended content to {args['filepath']}"
           )
       ]
   
class PatchContentToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_patch_content")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Insert content into an existing note relative to a heading, block reference, or frontmatter field.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the file (relative to vault root)",
                       "format": "path"
                   },
                   "operation": {
                       "type": "string",
                       "description": "Operation to perform (append, prepend, or replace)",
                       "enum": ["append", "prepend", "replace"]
                   },
                   "target_type": {
                       "type": "string",
                       "description": "Type of target to patch",
                       "enum": ["heading", "block", "frontmatter"]
                   },
                   "target": {
                       "type": "string", 
                       "description": "Target identifier (heading path, block reference, or frontmatter field)"
                   },
                   "content": {
                       "type": "string",
                       "description": "Content to insert"
                   }
               },
               "required": ["filepath", "operation", "target_type", "target", "content"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if not all(k in args for k in ["filepath", "operation", "target_type", "target", "content"]):
           raise RuntimeError("filepath, operation, target_type, target and content arguments required")

       api_key, host, port = get_obsidian_config()
       api = obsidian.Obsidian(api_key=api_key, host=host, port=port)
       api.patch_content(
           args.get("filepath", ""),
           args.get("operation", ""),
           args.get("target_type", ""),
           args.get("target", ""),
           args.get("content", "")
       )

       return [
           TextContent(
               type="text",
               text=f"Successfully patched content in {args['filepath']}"
           )
       ]
       
class PutContentToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_put_content")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description=(
               "Create a new file or completely replace an existing file's content. "
               "WARNING: This overwrites the entire file. "
               "For adding content to existing files, use obsidian_append_content or obsidian_patch_content instead."
           ),
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the relevant file (relative to your vault root)",
                       "format": "path"
                   },
                   "content": {
                       "type": "string",
                       "description": "Complete content of the file (will overwrite existing content)"
                   }
               },
               "required": ["filepath", "content"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "filepath" not in args or "content" not in args:
           raise RuntimeError("filepath and content arguments required")

       api_key, host, port = get_obsidian_config()
       api = obsidian.Obsidian(api_key=api_key, host=host, port=port)
       api.put_content(args.get("filepath", ""), args["content"])

       return [
           TextContent(
               type="text",
               text=f"Successfully uploaded content to {args['filepath']}"
           )
       ]
   




class FuzzySearchToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_fuzzy_search")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Unified fuzzy search for files, tags, or properties in your vault. "
                "Finds matches using fuzzy string matching (e.g., 'reading' matches '📚 Reading'). "
                "Perfect for discovery when you don't know exact names. "
                "Returns ranked results with similarity scores."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to fuzzy match. Leave empty to list all items of the specified type."
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["files", "tags", "properties"],
                        "description": "What to search: 'files' for filenames, 'tags' for tags, 'properties' for property names"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default: 10, max: 50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": ["search_type"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        from difflib import SequenceMatcher

        search_type = args.get("search_type")
        if search_type not in ["files", "tags", "properties"]:
            raise RuntimeError(f"Invalid search_type: {search_type}. Must be 'files', 'tags', or 'properties'")

        query = args.get("query", "")
        limit = args.get("limit", 10)

        if not isinstance(limit, int) or limit < 1:
            raise RuntimeError(f"Invalid limit: {limit}. Must be a positive integer")

        api_key, host, port = get_obsidian_config()
        api = obsidian.Obsidian(api_key=api_key, host=host, port=port)

        if search_type == "files":
            # Use existing fuzzy_search_files method
            if not query:
                raise RuntimeError("query is required for file search")
            results = api.fuzzy_search_files(query, limit)

        elif search_type == "tags":
            # Get all unique tags from the vault using Dataview
            # Dataview can extract tags more reliably than manual parsing
            try:
                # Use Dataview to get all tags
                dv_query = 'TABLE tags FROM "" WHERE tags'
                dv_result = api.execute_dataview_query(dv_query, format="json")

                tag_counts = {}

                # Parse Dataview results to extract tags
                if isinstance(dv_result, dict) and 'values' in dv_result:
                    for row in dv_result['values']:
                        # row is typically [file_link, tags_value]
                        if len(row) >= 2:
                            tags_value = row[1]

                            # Handle different tag formats
                            if isinstance(tags_value, list):
                                # Array of tags
                                for tag in tags_value:
                                    if isinstance(tag, str):
                                        tag_name = tag.lstrip('#').strip()
                                    elif isinstance(tag, dict) and 'tag' in tag:
                                        tag_name = tag['tag'].lstrip('#').strip()
                                    else:
                                        continue

                                    if tag_name:
                                        tag_counts[tag_name] = tag_counts.get(tag_name, 0) + 1
                            elif isinstance(tags_value, str):
                                # Single tag
                                tag_name = tags_value.lstrip('#').strip()
                                if tag_name:
                                    tag_counts[tag_name] = tag_counts.get(tag_name, 0) + 1

                # If no tags found via Dataview, fall back to manual extraction
                if not tag_counts:
                    all_files = api.search_json({"glob": ["*.md", {"var": "path"}]})
                    for result in all_files[:100]:  # Limit to first 100 files for performance
                        filepath = result.get('result', '')
                        if not filepath:
                            continue

                        try:
                            metadata = api.get_file_metadata(filepath)
                            tags = metadata.get('tags', [])

                            if isinstance(tags, list):
                                for tag in tags:
                                    if isinstance(tag, dict) and 'tag' in tag:
                                        tag_name = tag['tag'].lstrip('#').strip()
                                    elif isinstance(tag, str):
                                        tag_name = tag.lstrip('#').strip()
                                    else:
                                        continue

                                    if tag_name:
                                        tag_counts[tag_name] = tag_counts.get(tag_name, 0) + 1
                        except:
                            continue

                # Fuzzy match against tags
                if query:
                    scored_tags = []
                    for tag, count in tag_counts.items():
                        score = SequenceMatcher(None, query.lower(), tag.lower()).ratio()
                        scored_tags.append({
                            "name": tag,
                            "score": score,
                            "file_count": count
                        })

                    # Sort by score and limit
                    scored_tags.sort(key=lambda x: x['score'], reverse=True)
                    results = scored_tags[:limit]
                else:
                    # No query - return all tags sorted by file count
                    results = [
                        {"name": tag, "score": 1.0, "file_count": count}
                        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
                    ][:limit]

            except Exception as e:
                # If everything fails, return error message
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "error": f"Failed to extract tags: {str(e)}",
                            "results": []
                        }, indent=2, ensure_ascii=False)
                    )
                ]

        elif search_type == "properties":
            # Get all property names
            all_properties = api.list_all_properties()

            if query:
                # Fuzzy match against properties
                scored_properties = []
                for prop in all_properties:
                    score = SequenceMatcher(None, query.lower(), prop.lower()).ratio()
                    scored_properties.append({
                        "name": prop,
                        "score": score
                    })

                # Sort by score and limit
                scored_properties.sort(key=lambda x: x['score'], reverse=True)
                results = scored_properties[:limit]
            else:
                # No query - return all properties
                results = [{"name": prop, "score": 1.0} for prop in all_properties[:limit]]

        return [
            TextContent(
                type="text",
                text=json.dumps(results, indent=2, ensure_ascii=False)
            )
        ]

class CreateSmartTaskToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_create_smart_task")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Create a new smart task file with metadata, status buttons, and proper structure. Mimics the SmartTask template functionality.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_folder": {
                        "type": "string",
                        "description": "Path to the project folder where the task should be created (e.g., 'Work/Turing/Projects/MyProject')",
                        "format": "path"
                    },
                    "task_name": {
                        "type": "string",
                        "description": "Optional custom name for the task. If not provided, uses the project folder name."
                    },
                    "priority": {
                        "type": "string",
                        "description": "Task priority level (default: 🟡 Medium)",
                        "enum": ["🟢 Low", "🟡 Medium", "🔴 High", "🟣 Ultra-High"],
                        "default": "🟡 Medium"
                    },
                    "initial_notes": {
                        "type": "string",
                        "description": "Optional initial content for the Notes section"
                    }
                },
                "required": ["project_folder"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "project_folder" not in args:
            raise RuntimeError("project_folder argument missing in arguments")

        from datetime import datetime

        api_key, host, port = get_obsidian_config()
        api = obsidian.Obsidian(api_key=api_key, host=host, port=port)

        # Extract project name from folder path
        project_folder = args["project_folder"].strip("/")
        project_name = project_folder.split("/")[-1] if project_folder else "General"

        # Generate filename with timestamp
        date_str = datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Use custom task name if provided, otherwise use project name
        task_name = args.get("task_name", project_name)
        filename = f"{task_name} - {date_str}.md"

        # Full file path
        filepath = f"{project_folder}/{filename}" if project_folder else filename

        # Get priority (default to Medium)
        priority = args.get("priority", "🟡 Medium")

        # Get initial notes if provided
        initial_notes = args.get("initial_notes", "")

        # Generate tag from project name (lowercase, replace spaces with hyphens)
        tag = project_name.replace(" ", "-").lower()

        # Build the file content
        content = f"""---
project: {project_name}
status: 🔄 Not-Started
priority: {priority}
tags:
  - {tag}
created: {time_str}
time-completed:
---

## Meta Data Buttons

```meta-bind-embed
  [[metabind-button-definitions]]
```

## 📝 Notes

{initial_notes}

## 📎 Resources

"""

        # Create the file
        api.put_content(filepath, content)

        return [
            TextContent(
                type="text",
                text=f"Successfully created smart task at: {filepath}"
            )
        ]

def _stringify_property_value(value: Any) -> str:
    """Convert a frontmatter value into a readable string."""
    if isinstance(value, list):
        if not value:
            return "(empty list)"
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        for candidate in ("name", "title", "value", "path", "link"):
            if candidate in value:
                return str(value[candidate])
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return "(empty)"
    return str(value)


def _gather_property_statistics(api: obsidian.Obsidian, folder: str) -> tuple[dict[str, Any], int]:
    """Collect property usage, sample values, and example files for a folder."""
    from_clause = f'"{folder}"' if folder else '""'
    query = f'TABLE file.frontmatter FROM {from_clause} WHERE file.frontmatter'
    result = api.execute_dataview_query(query, format="json")

    property_stats: dict[str, Any] = {}
    for item in result:
        frontmatter = (item.get("result") or {}).get("file.frontmatter") or {}
        filename = item.get("filename", "")
        if not isinstance(frontmatter, dict):
            continue

        for prop, value in frontmatter.items():
            stats = property_stats.setdefault(prop, {
                "count": 0,
                "value_counter": Counter(),
                "sample_values": [],
                "sample_files": []
            })
            stats["count"] += 1

            value_str = _stringify_property_value(value)
            stats["value_counter"][value_str] += 1

            if value_str and value_str not in stats["sample_values"]:
                if len(stats["sample_values"]) < 3:
                    stats["sample_values"].append(value_str)

            if filename and filename not in stats["sample_files"]:
                if len(stats["sample_files"]) < 3:
                    stats["sample_files"].append(filename)

    return property_stats, len(result)


class SuggestColumnsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_suggest_columns")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Discover exactly which properties exist, how frequently they appear, and what values they hold. "
                "Use it when you need to know the precise frontmatter field names and value keywords before crafting a Dataview query."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "folder": {
                        "type": "string",
                        "description": "Optional vault folder to inspect (\"\" or omit to inspect the entire vault)."
                    },
                    "property_filter": {
                        "type": "string",
                        "description": "Case-insensitive substring to narrow the returned property names (e.g., 'status', 'reading')."
                    },
                    "value_filter": {
                        "type": "string",
                        "description": "Case-insensitive substring to only surface properties whose values mention the given term (e.g., 'read', 'completed')."
                    },
                    "max_properties": {
                        "type": "integer",
                        "description": "Maximum number of properties to return (default: 40).",
                        "default": 40,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "max_values": {
                        "type": "integer",
                        "description": "Limit the number of value counts/matching values per property (default: 5).",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20
                    }
                },
                "required": []
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        api_key, host, port = get_obsidian_config()
        api = obsidian.Obsidian(api_key=api_key, host=host, port=port)

        folder = args.get("folder", "")
        property_filter = args.get("property_filter", "").strip()
        value_filter = args.get("value_filter", "").strip()
        max_properties = args.get("max_properties", 40)
        max_values = args.get("max_values", 5)

        if not isinstance(max_properties, int) or max_properties < 1:
            raise RuntimeError("max_properties must be a positive integer")
        if not isinstance(max_values, int) or max_values < 1:
            raise RuntimeError("max_values must be a positive integer")

        try:
            property_stats, total_files = _gather_property_statistics(api, folder)

            property_filter_lower = property_filter.lower()
            value_filter_lower = value_filter.lower()
            properties_output = []

            for prop, stats in sorted(
                property_stats.items(),
                key=lambda item: item[1]["count"],
                reverse=True
            ):
                normalized_name = "".join(ch for ch in prop.lower() if ch.isalnum())

                matches_property = (
                    not property_filter_lower
                    or property_filter_lower in prop.lower()
                    or property_filter_lower in normalized_name
                )

                value_items = [
                    {"value": value, "count": count}
                    for value, count in stats["value_counter"].items()
                ]
                value_items.sort(key=lambda item: item["count"], reverse=True)

                matching_values = []
                if value_filter_lower:
                    matching_values = [
                        item for item in value_items
                        if value_filter_lower in item["value"].lower()
                    ]

                if property_filter_lower and not matches_property:
                    continue
                if value_filter_lower and not matching_values:
                    continue

                properties_output.append({
                    "name": prop,
                    "normalized_name": normalized_name,
                    "count": stats["count"],
                    "sample_values": stats["sample_values"],
                    "sample_files": stats["sample_files"],
                    "value_counts": value_items[:max_values],
                    "matching_values": matching_values[:max_values]
                })

                if len(properties_output) >= max_properties:
                    break

            output = {
                "folder": folder if folder else "entire vault",
                "total_files_analyzed": total_files,
                "properties_returned": len(properties_output),
                "properties": properties_output
            }

            return [
                TextContent(
                    type="text",
                    text=json.dumps(output, indent=2, ensure_ascii=False)
                )
            ]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "error": f"Failed to analyze folder: {str(e)}",
                        "folder": folder
                    }, indent=2, ensure_ascii=False)
                )
            ]


class GetPropertyValuesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_property_values")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Inspect an individual property and see the most common values it takes, plus sample files. "
                "Use obsidian_suggest_columns to discover property names before calling this tool."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "property_name": {
                        "type": "string",
                        "description": "Property name to get values for (e.g., 'reading_status', 'platform', 'status')"
                    },
                    "folder": {
                        "type": "string",
                        "description": "Optional: folder path to search in (e.g., 'Reading/Books'). Omit to search entire vault."
                    },
                    "max_values": {
                        "type": "integer",
                        "description": "Limit the number of value counts returned (default: 20).",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["property_name"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "property_name" not in args:
            raise RuntimeError("property_name argument required")

        api_key, host, port = get_obsidian_config()
        api = obsidian.Obsidian(api_key=api_key, host=host, port=port)

        property_name = args["property_name"]
        folder = args.get("folder", "")
        max_values = args.get("max_values", 20)

        if not isinstance(max_values, int) or max_values < 1:
            raise RuntimeError("max_values must be a positive integer")

        property_stats, _ = _gather_property_statistics(api, folder)
        stats = property_stats.get(property_name)
        if not stats:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "error": f"Property '{property_name}' not found in folder '{folder or 'entire vault'}'.",
                        "property": property_name,
                        "folder": folder or "entire vault"
                    }, indent=2, ensure_ascii=False)
                )
            ]

        value_counts = [
            {"value": value, "count": count}
            for value, count in stats["value_counter"].items()
        ]
        value_counts.sort(key=lambda x: x['count'], reverse=True)

        output = {
            "property": property_name,
            "folder": folder if folder else "entire vault",
            "total_unique_values": len(value_counts),
            "sample_values": stats["sample_values"],
            "sample_files": stats["sample_files"],
            "values": value_counts[:max_values]
        }

        return [
            TextContent(
                type="text",
                text=json.dumps(output, indent=2, ensure_ascii=False)
            )
        ]


class DataviewQueryToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_dataview_query")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Execute Dataview TABLE queries - the PRIMARY tool for searching, filtering, and aggregating vault data. "
                "This powerful query engine REPLACES many specialized tools. Use it for:\n"
                "• Finding files by properties (status, tags, dates)\n"
                "• Searching file content with contains() function\n"
                "• Getting recent files with file.mtime\n"
                "• Listing all property values (just SELECT the property column)\n"
                "• Complex filtering with AND/OR logic\n\n"
                "IMPORTANT: Only TABLE queries are supported (not LIST or TASK).\n\n"
                "Common patterns:\n"
                "• Search content: TABLE file.link FROM \"\" WHERE contains(file.content, \"keyword\")\n"
                "• Recent files: TABLE file.link, file.mtime FROM \"\" SORT file.mtime DESC LIMIT 10\n"
                "• Files by property: TABLE file.link, status FROM \"Work\" WHERE status = \"⚡ In-Progress\"\n"
                "• All property values: TABLE reading_status FROM \"Reading/Books\" WHERE reading_status\n"
                "• Group by property: TABLE rows.file.link FROM \"Reading/Books\" WHERE reading_status GROUP BY reading_status\n"
                "• Search in arrays: TABLE file.link FROM \"\" WHERE contains(tags, \"reading\")\n"
                "• Multiple conditions: TABLE title, rating FROM \"Reading/Books\" WHERE rating >= 4 AND contains(author, \"Smith\")\n"
                "• All files with property: TABLE file.link, tags FROM \"\" WHERE tags\n\n"
                "SYNTAX NOTES:\n"
                "• Use contains(field, \"value\") NOT field CONTAINS \"value\"\n"
                "• To list all values of a property: TABLE property_name FROM folder WHERE property_name\n"
                "• GROUP BY creates groups - use 'rows' to access items: TABLE rows.file.link FROM folder GROUP BY property\n"
                "• Arrays/tags: Use contains(tags, \"tag-name\") to search within tag arrays\n"
                "• format='json' for easier programmatic parsing of results\n\n"
                "Use obsidian_fuzzy_search to discover available properties and tags first."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "DQL TABLE query string. Format: TABLE <columns> FROM \"<folder>\" [WHERE <conditions>] [SORT <column> ASC|DESC] [LIMIT <n>]\n\n"
                            "Key syntax:\n"
                            "• Columns: property names, file.link, file.name, file.mtime, file.content\n"
                            "• FROM: Folder path in quotes (\"\" = all files, \"Folder/Path\" = specific folder)\n"
                            "• WHERE: Use =, !=, <, >, <=, >=, AND, OR\n"
                            "• contains(field, \"text\"): Search within field (use for arrays/tags/text)\n"
                            "• GROUP BY property: Groups results - use 'rows' to access grouped items\n"
                            "• SORT column ASC/DESC: Order results\n"
                            "• LIMIT n: Max results\n\n"
                            "Examples:\n"
                            "TABLE title, author FROM \"Reading/Books\" WHERE rating >= 4\n"
                            "TABLE reading_status FROM \"Reading/Books\" WHERE reading_status\n"
                            "TABLE rows.file.link FROM \"Work\" WHERE status GROUP BY status\n"
                            "TABLE file.link FROM \"\" WHERE contains(tags, \"project\")"
                        )
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "markdown_table"],
                        "default": "markdown_table",
                        "description": "Output format: 'json' for raw data or 'markdown_table' for formatted display"
                    }
                },
                "required": ["query"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "query" not in args:
            raise RuntimeError("query argument missing in arguments")

        api_key, host, port = get_obsidian_config()
        api = obsidian.Obsidian(api_key=api_key, host=host, port=port)

        format_type = args.get("format", "markdown_table")
        result = api.execute_dataview_query(args["query"], format=format_type)

        return [
            TextContent(
                type="text",
                text=result if format_type == "markdown_table" else json.dumps(result, indent=2, ensure_ascii=False)
            )
        ]
