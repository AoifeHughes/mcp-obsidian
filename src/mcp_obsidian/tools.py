from collections.abc import Sequence
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
import json
import os
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
            description="List files/directories in vault. Omit path for vault root, or specify a directory path.",
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
            description="Read file content(s). Accepts a single file path string or array of paths. Multiple files are concatenated with headers.",
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

        # Handle both string and array inputs
        if isinstance(filepath, list):
            # Multiple files - use batch method
            content = api.get_batch_file_contents(filepath)
        else:
            # Single file
            content = api.get_file_contents(filepath)
            content = json.dumps(content, indent=2, ensure_ascii=False)

        return [
            TextContent(
                type="text",
                text=content
            )
        ]

class GetFileMetadataToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_file_metadata")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get metadata for a specific file including frontmatter properties, tags, and file statistics. This returns only the metadata without file content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file (relative to vault root)",
                        "format": "path"
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

        metadata = api.get_file_metadata(args["filepath"])

        return [
            TextContent(
                type="text",
                text=json.dumps(metadata, indent=2, ensure_ascii=False)
            )
        ]
    
class SearchToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_simple_search")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Search vault for text matches with context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text to search for"
                    },
                    "context_length": {
                        "type": "integer",
                        "description": "Context chars around match (default: 100)",
                        "default": 100
                    }
                },
                "required": ["query"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "query" not in args:
            raise RuntimeError("query argument missing in arguments")

        context_length = args.get("context_length", 100)
        
        api_key, host, port = get_obsidian_config()
        api = obsidian.Obsidian(api_key=api_key, host=host, port=port)
        results = api.search(args["query"], context_length)
        
        formatted_results = []
        for result in results:
            formatted_matches = []
            for match in result.get('matches', []):
                context = match.get('context', '')
                match_pos = match.get('match', {})
                start = match_pos.get('start', 0)
                end = match_pos.get('end', 0)
                
                formatted_matches.append({
                    'context': context,
                    'match_position': {'start': start, 'end': end}
                })
                
            formatted_results.append({
                'filename': result.get('filename', ''),
                'score': result.get('score', 0),
                'matches': formatted_matches
            })

        return [
            TextContent(
                type="text",
                text=json.dumps(formatted_results, indent=2, ensure_ascii=False)
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
           description="Create a new file in your vault or update the content of an existing one in your vault.",
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
                       "description": "Content of the file you would like to upload"
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
   

class DeleteFileToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_delete_file")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Delete a file or directory from the vault.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the file or directory to delete (relative to vault root)",
                       "format": "path"
                   },
                   "confirm": {
                       "type": "boolean",
                       "description": "Confirmation to delete the file (must be true)",
                       "default": False
                   }
               },
               "required": ["filepath", "confirm"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "filepath" not in args:
           raise RuntimeError("filepath argument missing in arguments")

       if not args.get("confirm", False):
           raise RuntimeError("confirm must be set to true to delete a file")

       api_key, host, port = get_obsidian_config()
       api = obsidian.Obsidian(api_key=api_key, host=host, port=port)
       api.delete_file(args["filepath"])

       return [
           TextContent(
               type="text",
               text=f"Successfully deleted {args['filepath']}"
           )
       ]
   
class ComplexSearchToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_complex_search")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Advanced search using JsonLogic queries. Supports 'and', 'or', 'glob' (file patterns), and 'regexp' (regex). Vars: 'path', 'content', 'frontmatter'. Example: {\"and\": [{\"glob\": [\"*.md\", {\"var\": \"path\"}]}, {\"regexp\": [\"keyword\", {\"var\": \"content\"}]}]}",
           inputSchema={
               "type": "object",
               "properties": {
                   "query": {
                       "type": "object",
                       "description": "JsonLogic query object. Use 'glob' for paths, 'regexp' for content matching, 'and'/'or' for combining."
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
       results = api.search_json(args.get("query", ""))

       return [
           TextContent(
               type="text",
               text=json.dumps(results, indent=2, ensure_ascii=False)
           )
       ]

class PeriodicNotesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_periodic_notes")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get periodic note(s). Set recent=false for current note only, or recent=true for list of recent notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "Period type",
                        "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"]
                    },
                    "recent": {
                        "type": "boolean",
                        "description": "Get recent list (true) or current note only (false, default)",
                        "default": False
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max notes when recent=true (default: 5, max: 50)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "include_content": {
                        "type": "boolean",
                        "description": "Include content when recent=true (default: false)",
                        "default": False
                    },
                    "type": {
                        "type": "string",
                        "description": "Data type when recent=false: 'content' or 'metadata' (default: content)",
                        "default": "content",
                        "enum": ["content", "metadata"]
                    }
                },
                "required": ["period"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "period" not in args:
            raise RuntimeError("period argument missing in arguments")

        period = args["period"]
        valid_periods = ["daily", "weekly", "monthly", "quarterly", "yearly"]
        if period not in valid_periods:
            raise RuntimeError(f"Invalid period: {period}. Must be one of: {', '.join(valid_periods)}")

        api_key, host, port = get_obsidian_config()
        api = obsidian.Obsidian(api_key=api_key, host=host, port=port)

        recent = args.get("recent", False)

        if recent:
            # Get list of recent notes
            limit = args.get("limit", 5)
            if not isinstance(limit, int) or limit < 1:
                raise RuntimeError(f"Invalid limit: {limit}. Must be a positive integer")

            include_content = args.get("include_content", False)
            if not isinstance(include_content, bool):
                raise RuntimeError(f"Invalid include_content: {include_content}. Must be a boolean")

            results = api.get_recent_periodic_notes(period, limit, include_content)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(results, indent=2, ensure_ascii=False)
                )
            ]
        else:
            # Get current note only
            note_type = args.get("type", "content")
            valid_types = ["content", "metadata"]
            if note_type not in valid_types:
                raise RuntimeError(f"Invalid type: {note_type}. Must be one of: {', '.join(valid_types)}")

            content = api.get_periodic_note(period, note_type)
            return [
                TextContent(
                    type="text",
                    text=content
                )
            ]
        
class RecentChangesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_recent_changes")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get recently modified files.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max files (default: 10, max: 100)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "days": {
                        "type": "integer",
                        "description": "Modified within N days (default: 90)",
                        "minimum": 1,
                        "default": 90
                    }
                }
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        limit = args.get("limit", 10)
        if not isinstance(limit, int) or limit < 1:
            raise RuntimeError(f"Invalid limit: {limit}. Must be a positive integer")

        days = args.get("days", 90)
        if not isinstance(days, int) or days < 1:
            raise RuntimeError(f"Invalid days: {days}. Must be a positive integer")

        api_key, host, port = get_obsidian_config()
        api = obsidian.Obsidian(api_key=api_key, host=host, port=port)
        results = api.get_recent_changes(limit, days)

        return [
            TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )
        ]

class GetFilesWithPropertyToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_files_with_property")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get files with a specific frontmatter property. Use obsidian_get_property_values first if you don't know what values exist.",
            inputSchema={
                "type": "object",
                "properties": {
                    "property_name": {
                        "type": "string",
                        "description": "Property name (e.g., 'reading_status', 'tags')"
                    },
                    "property_value": {
                        "type": "string",
                        "description": "Optional: filter by exact value"
                    }
                },
                "required": ["property_name"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "property_name" not in args:
            raise RuntimeError("property_name argument missing in arguments")

        api_key, host, port = get_obsidian_config()
        api = obsidian.Obsidian(api_key=api_key, host=host, port=port)
        results = api.get_files_with_property(
            args["property_name"],
            args.get("property_value")
        )

        # Extract just the filenames for cleaner output
        filenames = [result.get("filename") for result in results if result.get("filename")]

        response_data = {
            "property": args["property_name"],
            "count": len(filenames),
            "files": filenames
        }
        if "property_value" in args:
            response_data["value_filter"] = args["property_value"]

        return [
            TextContent(
                type="text",
                text=json.dumps(response_data, indent=2, ensure_ascii=False)
            )
        ]

class GetPropertyValuesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_property_values")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Discover all values for a property across vault. Use this BEFORE obsidian_get_files_with_property when you don't know what values exist.",
            inputSchema={
                "type": "object",
                "properties": {
                    "property_name": {
                        "type": "string",
                        "description": "Property name to check values for"
                    }
                },
                "required": ["property_name"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "property_name" not in args:
            raise RuntimeError("property_name argument missing in arguments")

        api_key, host, port = get_obsidian_config()
        api = obsidian.Obsidian(api_key=api_key, host=host, port=port)
        results = api.get_property_values(args["property_name"])

        # Extract unique values only
        unique_values = set()
        for result in results:
            value = result.get("result")
            if value is not None:
                # Convert to JSON string for consistent deduplication of complex types
                value_key = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
                unique_values.add(value_key)

        # Convert back to original types and sort
        final_values = []
        for v in unique_values:
            try:
                # Try to parse back if it was JSON
                final_values.append(json.loads(v))
            except (json.JSONDecodeError, TypeError):
                # It's a simple value
                final_values.append(v)

        # Sort for consistent output
        try:
            final_values.sort()
        except TypeError:
            # Can't sort mixed types, just return as is
            pass

        return [
            TextContent(
                type="text",
                text=json.dumps(final_values, indent=2, ensure_ascii=False)
            )
        ]

class ListAllPropertiesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_list_all_properties")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="List all property names in vault. Use this FIRST if you don't know what properties exist.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        api_key, host, port = get_obsidian_config()
        api = obsidian.Obsidian(api_key=api_key, host=host, port=port)
        properties = api.list_all_properties()

        return [
            TextContent(
                type="text",
                text=json.dumps(properties, indent=2, ensure_ascii=False)
            )
        ]

class FuzzySearchFilesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_fuzzy_search_files")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Search for files by name using fuzzy matching. Returns closest matching files sorted by similarity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to match against file names"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default: 10, max: 50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": ["query"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "query" not in args:
            raise RuntimeError("query argument missing in arguments")

        limit = args.get("limit", 10)
        if not isinstance(limit, int) or limit < 1:
            raise RuntimeError(f"Invalid limit: {limit}. Must be a positive integer")

        api_key, host, port = get_obsidian_config()
        api = obsidian.Obsidian(api_key=api_key, host=host, port=port)
        results = api.fuzzy_search_files(args["query"], limit)

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

class DataviewQueryToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_dataview_query")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Execute Dataview TABLE queries for flexible data retrieval from your Obsidian vault. "
                "IMPORTANT: Only TABLE queries are supported (not LIST or TASK). "
                "Use WHERE clauses, comparison operators, SORT, LIMIT, and GROUP BY for complex filtering. "
                "Perfect for filtering books by rating, finding high-priority tasks, or aggregating data across files. "
                "\n\nExample queries:"
                "\n- TABLE title, author, rating FROM \"Reading/Books\" WHERE reading_status = \"📚 Reading\""
                "\n- TABLE file.link, status, priority FROM \"Work\" WHERE status = \"⚡ In-Progress\" AND priority = \"🔴 High\""
                "\n- TABLE game_title, platform, star_rating FROM \"Gaming/Games\" WHERE play_status = \"🎮 Playing\" SORT star_rating DESC"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "DQL TABLE query string. Format: TABLE <columns> FROM \"<folder>\" [WHERE <conditions>] [SORT <column> ASC|DESC] [LIMIT <n>]\n"
                            "Supported features:\n"
                            "- Columns: Property names, file.link, file.name, file.mtime, etc.\n"
                            "- FROM: Folder path in quotes (e.g., \"Reading/Books\")\n"
                            "- WHERE: Filters with =, !=, <, >, <=, >=, contains, AND, OR\n"
                            "- SORT: Column name with ASC/DESC\n"
                            "- LIMIT: Number of results\n"
                            "Example: 'TABLE title, author FROM \"Reading/Books\" WHERE rating >= 4 SORT title ASC LIMIT 10'"
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

class SuggestColumnsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_suggest_columns")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Suggest relevant columns for Dataview queries based on content type. "
                "Discovers available frontmatter properties in a specific folder or across the vault, "
                "helping you build accurate TABLE queries. Use this before obsidian_dataview_query "
                "to understand what fields are available for querying."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "folder": {
                        "type": "string",
                        "description": (
                            "Folder path to analyze (e.g., 'Reading/Books', 'Gaming/Games', 'Work/Turing/Projects'). "
                            "Omit to analyze all files in the vault."
                        )
                    },
                    "content_type": {
                        "type": "string",
                        "enum": ["books", "games", "tasks", "all"],
                        "default": "all",
                        "description": "Filter suggestions by content type for more relevant results"
                    }
                },
                "required": []
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        api_key, host, port = get_obsidian_config()
        api = obsidian.Obsidian(api_key=api_key, host=host, port=port)

        folder = args.get("folder")
        content_type = args.get("content_type", "all")

        # Get all properties
        all_properties = api.list_all_properties()

        # If folder is specified, filter to only properties found in that folder
        if folder:
            # Use JsonLogic to find files in the folder and extract their properties
            query = {
                "and": [
                    {"glob": [f"{folder}/*.md", {"var": "path"}]},
                    {"var": "frontmatter"}
                ]
            }

            try:
                results = api.search_json(query)
                folder_properties = set()
                for result in results:
                    if isinstance(result.get('result'), dict):
                        folder_properties.update(result['result'].keys())

                all_properties = sorted(list(folder_properties))
            except Exception as e:
                # If folder search fails, fall back to all properties
                pass

        # Define common property sets by content type
        property_suggestions = {
            "books": {
                "common": ["title", "author", "reading_status", "rating", "publication_date", "series", "genres"],
                "additional": ["publisher", "pages", "isbn", "date_started", "date_finished", "calibre_id"]
            },
            "games": {
                "common": ["game_title", "platform", "play_status", "star_rating", "genre", "release_date"],
                "additional": ["developer", "publisher", "game_modes", "themes", "rating", "igdb_id"]
            },
            "tasks": {
                "common": ["status", "priority", "project", "created", "time-completed", "due"],
                "additional": ["tags", "file.link", "file.mtime"]
            }
        }

        # Build response based on content type
        if content_type != "all" and content_type in property_suggestions:
            suggestions = property_suggestions[content_type]
            available_common = [p for p in suggestions["common"] if p in all_properties]
            available_additional = [p for p in suggestions["additional"] if p in all_properties]

            response_text = f"# Suggested Columns for {content_type.capitalize()}\n\n"
            response_text += "## Common Properties\n"
            response_text += ", ".join(available_common) + "\n\n"
            response_text += "## Additional Properties\n"
            response_text += ", ".join(available_additional) + "\n\n"
            response_text += "## All Available Properties\n"
            response_text += ", ".join(all_properties)
        else:
            response_text = f"# Available Properties{' in ' + folder if folder else ''}\n\n"
            response_text += ", ".join(all_properties)
            response_text += "\n\n## Common Query Patterns\n"
            response_text += "- Books: title, author, reading_status, rating\n"
            response_text += "- Games: game_title, platform, play_status, star_rating\n"
            response_text += "- Tasks: status, priority, project, created, due\n"
            response_text += "- Files: file.link, file.name, file.mtime, file.ctime\n"

        return [
            TextContent(
                type="text",
                text=response_text
            )
        ]
