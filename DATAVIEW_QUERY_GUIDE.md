# Dataview Query Tools Guide

This document describes the new flexible table query system for the Obsidian MCP server.

## Overview

Two new tools have been added to enable AI models to query your Obsidian vault using Dataview Query Language (DQL):

1. **`obsidian_dataview_query`** - Execute TABLE queries with flexible filtering, sorting, and formatting
2. **`obsidian_suggest_columns`** - Discover available properties/columns for building queries

## Tool 1: obsidian_dataview_query

### Description
Execute Dataview TABLE queries for flexible data retrieval from your Obsidian vault. Supports WHERE clauses, comparison operators, SORT, LIMIT, and GROUP BY for complex filtering.

### Important Limitations
- **Only TABLE queries are supported** (not LIST or TASK queries)
- This is a limitation of the Obsidian Local REST API

### Parameters
- `query` (required): DQL TABLE query string
- `format` (optional): Output format - "markdown_table" (default) or "json"

### Query Syntax
```
TABLE <columns> FROM "<folder>" [WHERE <conditions>] [SORT <column> ASC|DESC] [LIMIT <n>]
```

**Supported features:**
- **Columns**: Property names, `file.link`, `file.name`, `file.mtime`, etc.
- **FROM**: Folder path in quotes (e.g., `"Reading/Books"`)
- **WHERE**: Filters with `=`, `!=`, `<`, `>`, `<=`, `>=`, `contains`, `AND`, `OR`
- **SORT**: Column name with `ASC`/`DESC`
- **LIMIT**: Number of results

### Example Queries

#### Books
```dql
TABLE title, author, rating FROM "Reading/Books" WHERE rating = "⭐⭐⭐⭐⭐"
TABLE title, author, reading_status FROM "Reading/Books" WHERE reading_status = "📚 Reading"
TABLE title, author FROM "Reading/Books" SORT publication_year DESC LIMIT 10
```

#### Games
```dql
TABLE game_title, platform, star_rating FROM "Gaming/Games" WHERE play_status = "🎮 Playing"
TABLE game_title, genre, rating FROM "Gaming/Games" WHERE star_rating = "⭐⭐⭐⭐⭐" SORT rating DESC
```

#### Tasks
```dql
TABLE file.link as Task, status, priority, project FROM "Work" WHERE status = "⚡ In-Progress"
TABLE file.link, status, priority FROM "Work" WHERE status = "⚡ In-Progress" AND priority = "🔴 High"
TABLE file.link, project, created FROM "Personal" WHERE status = "🔄 Not-Started" SORT created DESC
```

### Example Output

**Markdown Table Format** (default):
```markdown
| File | title | author | rating |
| --- | --- | --- | --- |
| [[Reading/Books/book1.md]] | The Great Book | Jane Doe | ⭐⭐⭐⭐⭐ |
| [[Reading/Books/book2.md]] | Another Great Book | John Smith | ⭐⭐⭐⭐⭐ |
```

**JSON Format**:
```json
[
  {
    "filename": "Reading/Books/book1.md",
    "result": {
      "title": "The Great Book",
      "author": "Jane Doe",
      "rating": "⭐⭐⭐⭐⭐"
    }
  }
]
```

## Tool 2: obsidian_suggest_columns

### Description
Discover available frontmatter properties in your vault to help build accurate queries. Shows which columns are available for querying specific content types.

### Parameters
- `folder` (optional): Folder path to analyze (e.g., `"Reading/Books"`, `"Gaming/Games"`)
- `content_type` (optional): Filter by content type - "books", "games", "tasks", or "all" (default)

### Example Usage

**Discover book properties:**
```
folder: "Reading/Books"
content_type: "books"
```

**Output:**
```
# Suggested Columns for Books

## Common Properties
title, author, reading_status, rating, publication_date, series, genres

## Additional Properties
publisher, pages, isbn, date_started, date_finished, calibre_id

## All Available Properties
title, author, reading_status, rating, publication_date, ...
```

**Get all vault properties:**
```
content_type: "all"
```

## Common Use Cases

### 1. "Get a table of all books currently being read"

**Workflow:**
1. Use `obsidian_suggest_columns` with `folder="Reading/Books"` and `content_type="books"`
2. Identify relevant columns: `title`, `author`, `reading_status`, `date_started`
3. Execute query:
   ```dql
   TABLE title, author, date_started FROM "Reading/Books" WHERE reading_status = "📚 Reading"
   ```

### 2. "Show high-priority tasks in progress"

**Workflow:**
1. Use `obsidian_suggest_columns` with `content_type="tasks"`
2. Identify columns: `status`, `priority`, `project`, `created`
3. Execute query:
   ```dql
   TABLE file.link as Task, status, priority, project FROM "Work"
   WHERE status = "⚡ In-Progress" AND priority = "🔴 High"
   ```

### 3. "Find top-rated games on Nintendo Switch"

**Workflow:**
1. Use `obsidian_suggest_columns` with `folder="Gaming/Games"` and `content_type="games"`
2. Identify columns: `game_title`, `platform`, `star_rating`
3. Execute query:
   ```dql
   TABLE game_title, platform, star_rating FROM "Gaming/Games"
   WHERE platform contains "Nintendo Switch" AND star_rating = "⭐⭐⭐⭐⭐"
   SORT star_rating DESC
   ```

## Property Schema Reference

### Books (Reading/Books/)
- **Common**: `title`, `author`, `reading_status`, `rating`, `publication_date`, `series`, `genres`
- **Additional**: `publisher`, `pages`, `isbn`, `date_started`, `date_finished`, `calibre_id`, `publication_year`, `languages`, `tags`, `cover`, `formats`, `identifiers`

### Games (Gaming/Games/)
- **Common**: `game_title`, `platform`, `play_status`, `star_rating`, `genre`, `release_date`
- **Additional**: `developer`, `publisher`, `game_modes`, `themes`, `rating`, `igdb_id`, `aggregated_rating`, `keywords`, `summary`, `storyline`, `player_perspectives`

### Tasks (Work/, Personal/)
- **Common**: `status`, `priority`, `project`, `created`, `time-completed`, `due`
- **Additional**: `tags`, `file.link`, `file.name`, `file.mtime`, `file.ctime`

### File Metadata (All files)
- `file.link` - Wikilink to the file
- `file.name` - File name without extension
- `file.path` - Full file path
- `file.mtime` - Last modified time
- `file.ctime` - Creation time
- `file.size` - File size in bytes

## Status Values Reference

### Reading Status (Books)
- `📖 Want to Read`
- `📚 Reading`
- `✅ Completed`
- `⏸️ On Hold`
- `❌ DNF` (Did Not Finish)

### Play Status (Games)
- `🔄 Not Played`
- `🎮 Playing`
- `⏸️ Want to Play`
- `✅ Completed`
- `❌ Dropped`
- `🔄 Want to Return to`
- `🚫 Not Interested`

### Task Status
- `🔄 Not-Started`
- `⚡ In-Progress`
- `✅ Done`
- `📦 Archived`

### Priority
- `🟢 Low`
- `🟡 Medium`
- `🔴 High`
- `🟣 Ultra-High`

### Rating/Star Rating
- `⭐` through `⭐⭐⭐⭐⭐`
- `Not Rated`

## Testing

Test scripts are available in the MCP server directory:

```bash
cd "AI Tools/mcp-obsidian"

# Test basic functionality
python test_table_format.py

# Debug raw API responses
python debug_query.py
```

## Implementation Details

### Files Modified
1. **`src/mcp_obsidian/obsidian.py`**
   - Added `execute_dataview_query()` method
   - Added `_format_dataview_as_table()` helper for markdown formatting

2. **`src/mcp_obsidian/tools.py`**
   - Added `DataviewQueryToolHandler` class
   - Added `SuggestColumnsToolHandler` class

3. **`src/mcp_obsidian/server.py`**
   - Registered new tool handlers

### Architecture
- **API Layer**: `obsidian.py` handles HTTP requests to Local REST API
- **Tool Layer**: `tools.py` provides MCP tool interfaces
- **Server Layer**: `server.py` registers and routes tool calls

### Data Flow
1. AI model calls `obsidian_dataview_query` with DQL query
2. Tool handler validates query and calls `Obsidian.execute_dataview_query()`
3. API wrapper POSTs query to Local REST API with `Content-Type: application/vnd.olrapi.dataview.dql+txt`
4. API returns list of `{filename, result}` objects
5. Formatter converts to markdown table or returns JSON
6. Result returned to AI model

## Troubleshooting

### "No results found"
- Check that the folder path exists and is spelled correctly
- Verify property values match exactly (including emoji status icons)
- Use `obsidian_suggest_columns` to discover actual property names

### "Only TABLE dataview queries are supported"
- Ensure query starts with `TABLE` (not `LIST` or `TASK`)
- This is a limitation of the Obsidian Local REST API

### "The query you provided could not be processed"
- Check DQL syntax (see examples above)
- Ensure folder paths are in quotes: `FROM "Reading/Books"`
- Verify property names exist using `obsidian_suggest_columns`

### Empty or incorrect results
- Use `obsidian_get_property_values` to see actual property values
- Remember that string comparisons are case-sensitive
- Emoji status values must match exactly

## Future Enhancements (Optional)

Potential improvements for future development:

1. **Query Presets**: Common queries as templates
   - "high_priority_tasks", "currently_reading_books", "top_rated_games"

2. **Aggregation Functions**: COUNT, SUM, AVG, GROUP BY
   - Currently GROUP BY is mentioned but not specifically tested

3. **Cross-File Relationships**: Follow links between files
   - Query related files (e.g., all books in a series)

4. **Query Builder**: Structured query construction
   - Alternative to raw DQL strings for simpler queries

5. **Caching**: Cache query results for faster repeated access
   - Could significantly improve performance for dashboards

## Conclusion

These tools provide powerful, flexible querying capabilities for your Obsidian vault, enabling AI models to:
- Discover available data schemas
- Build complex filtered queries
- Retrieve tabular data with proper formatting
- Support all content types (books, games, tasks, notes)

The implementation leverages existing infrastructure (Dataview plugin + Local REST API) for reliability and maintainability.
