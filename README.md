# MCP server for Obsidian

MCP server to interact with Obsidian via the Local REST API community plugin.

<a href="https://glama.ai/mcp/servers/3wko1bhuek"><img width="380" height="200" src="https://glama.ai/mcp/servers/3wko1bhuek/badge" alt="server for Obsidian MCP server" /></a>

## Components

### Tools

The server implements multiple tools to interact with Obsidian:

#### Core File Operations
- **list_files_in_vault**: Lists all files and directories in the root directory of your Obsidian vault
- **list_files_in_dir**: Lists all files and directories in a specific Obsidian directory
- **get_file_contents**: Return the content of a single file in your vault
- **batch_get_file_contents**: Get contents of multiple files at once
- **search**: Search for documents matching a specified text query across all files in the vault
- **complex_search**: Advanced search using JsonLogic or Dataview Query Language
- **patch_content**: Insert content into an existing note relative to a heading, block reference, or frontmatter field
- **append_content**: Append content to a new or existing file in the vault
- **put_content**: Create or completely replace file content
- **delete_file**: Delete a file or directory from your vault

#### Periodic Notes
- **get_periodic_note**: Get current periodic note (daily, weekly, monthly, quarterly, yearly)
- **get_recent_periodic_notes**: Get list of recent periodic notes
- **get_recent_changes**: Get recently modified files in the vault

#### Game Management
- **obsidian_search_games**: Search for games in IGDB and GiantBomb databases
- **obsidian_add_game**: Create a new game file with metadata from IGDB/GiantBomb
- **obsidian_enrich_game**: Update existing game file with latest metadata

#### Book Management (Calibre Integration)
- **obsidian_search_books**: Search for books in your Calibre library
- **obsidian_import_book_from_calibre**: Import a book from Calibre with metadata and cover art
- **obsidian_update_book**: Update existing book file with latest Calibre metadata
- **obsidian_sync_calibre**: Batch import multiple books from Calibre library

#### GitHub Integration
- **obsidian_import_github_issue**: Import a GitHub issue as an Obsidian task with AI-powered metadata extraction

#### Task Management
- **obsidian_create_smart_task**: Create a new smart task file with metadata, status buttons, and proper structure (mimics SmartTask template)

### Example prompts

Its good to first instruct Claude to use Obsidian. Then it will always call the tool.

#### Core Operations
- Get the contents of the last architecture call note and summarize them
- Search for all files where Azure CosmosDb is mentioned and quickly explain to me the context in which it is mentioned
- Summarize the last meeting notes and put them into a new note 'summary meeting.md'. Add an introduction so that I can send it via email.

#### Game Management
- Search for "The Witcher 3" and add it to my gaming vault
- Show me all games in the IGDB database matching "Final Fantasy"
- Update the metadata for my Minecraft game file

#### Book Management
- Import "The Name of the Wind" from my Calibre library
- Search my Calibre library for books by Brandon Sanderson
- Sync the first 10 books from my Calibre library to Obsidian

#### GitHub Integration
- Import GitHub issue #42 from owner/repo as a task in my Work/Projects/ProjectName folder
- Convert https://github.com/owner/repo/issues/123 into an Obsidian task

#### Task Management
- Create a new task in my Work/Turing/Projects/Documentation folder for updating the README
- Make a high-priority task called "Fix bug in authentication" in Personal/Projects/MyApp

## Configuration

### Required: Obsidian REST API Key

The OBSIDIAN_API_KEY can be configured in two ways:

1. **Add to MCP server config (preferred)**

```json
{
  "mcp-obsidian": {
    "command": "uvx",
    "args": ["mcp-obsidian"],
    "env": {
      "OBSIDIAN_API_KEY": "<your_api_key_here>",
      "OBSIDIAN_HOST": "127.0.0.1",
      "OBSIDIAN_PORT": "27124"
    }
  }
}
```

2. **Create a `.env` file** in the working directory:

```
OBSIDIAN_API_KEY=your_api_key_here
OBSIDIAN_HOST=127.0.0.1
OBSIDIAN_PORT=27124
```

Note:
- You can find the API key in the Obsidian Local REST API plugin settings
- Default port is 27124 if not specified
- Default host is 127.0.0.1 if not specified

### Optional: Centralized API Keys (for Content Management Tools)

For game, book, and GitHub integration features, create a `Keys/api_keys.json` file in your vault root:

```json
{
  "igdb": {
    "client_id": "your_twitch_client_id",
    "client_secret": "your_twitch_client_secret"
  },
  "giantbomb": {
    "api_key": "your_giantbomb_api_key"
  },
  "calibre": {
    "library_path": "/path/to/calibre/library"
  },
  "llm": {
    "api_base": "http://localhost:11434/v1",
    "model": "llama.cpp"
  },
  "github": {
    "token": "your_github_token"
  }
}
```

See `Keys/README.md` in your vault for detailed setup instructions.

## Running as HTTP Server

The MCP Obsidian server can run as an HTTP server with Server-Sent Events (SSE) transport, allowing web-based clients and remote access.

### Quick Start

```bash
# Install dependencies
uv sync

# Run the HTTP server
uv run mcp-obsidian-http

# Or run directly
uv run python serve_http.py
```

The server will start at `http://127.0.0.1:8000` by default.

### Configuration

Configure the HTTP server using environment variables:

```bash
# Server configuration
export MCP_HTTP_HOST=127.0.0.1  # Host to bind to (default: 127.0.0.1)
export MCP_HTTP_PORT=8000       # Port to bind to (default: 8000)

# Obsidian configuration (same as stdio mode)
export OBSIDIAN_API_KEY=your_api_key_here
export OBSIDIAN_HOST=127.0.0.1
export OBSIDIAN_PORT=27124

# Run the server
uv run mcp-obsidian-http
```

Or use a `.env` file in the project directory:

```
MCP_HTTP_HOST=127.0.0.1
MCP_HTTP_PORT=8000
OBSIDIAN_API_KEY=your_api_key_here
OBSIDIAN_HOST=127.0.0.1
OBSIDIAN_PORT=27124
```

### Endpoints

- **Health Check**: `GET http://127.0.0.1:8000/health` - Returns server health status
- **SSE Endpoint**: `GET http://127.0.0.1:8000/sse` - Server-Sent Events connection
- **Messages**: `POST http://127.0.0.1:8000/messages` - MCP message endpoint

### Usage with MCP Clients

Connect your MCP client to the SSE endpoint:

```typescript
const client = new MCPClient({
  transport: 'sse',
  url: 'http://127.0.0.1:8000/sse'
});
```

## Quickstart

### Install

#### Obsidian REST API

You need the Obsidian REST API community plugin running: https://github.com/coddingtonbear/obsidian-local-rest-api

Install and enable it in the settings and copy the api key.

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`

On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  
```json
{
  "mcpServers": {
    "mcp-obsidian": {
      "command": "uv",
      "args": [
        "--directory",
        "<dir_to>/mcp-obsidian",
        "run",
        "mcp-obsidian"
      ],
      "env": {
        "OBSIDIAN_API_KEY": "<your_api_key_here>",
        "OBSIDIAN_HOST": "<your_obsidian_host>",
        "OBSIDIAN_PORT": "<your_obsidian_port>"
      }
    }
  }
}
```
</details>

<details>
  <summary>Published Servers Configuration</summary>
  
```json
{
  "mcpServers": {
    "mcp-obsidian": {
      "command": "uvx",
      "args": [
        "mcp-obsidian"
      ],
      "env": {
        "OBSIDIAN_API_KEY": "<YOUR_OBSIDIAN_API_KEY>",
        "OBSIDIAN_HOST": "<your_obsidian_host>",
        "OBSIDIAN_PORT": "<your_obsidian_port>"
      }
    }
  }
}
```
</details>

## Development

### Building

To prepare the package for distribution:

1. Sync dependencies and update lockfile:
```bash
uv sync
```

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).

You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/mcp-obsidian run mcp-obsidian
```

Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.

You can also watch the server logs with this command:

```bash
tail -n 20 -f ~/Library/Logs/Claude/mcp-server-mcp-obsidian.log
```
