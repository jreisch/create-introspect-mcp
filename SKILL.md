---
name: create-introspect-mcp
description: Guide for creating introspection-based MCP servers that provide API documentation and search capabilities for any Python module. Use when building MCP servers for Python library documentation, API reference systems, or when users request "create an MCP server for [module name]" or "build introspection server for Python library".
---

# Create Introspection MCP Server

Create high-quality MCP servers that introspect Python modules and provide comprehensive API documentation search capabilities through the Model Context Protocol.

## Overview

This skill guides you through creating an introspection-based MCP server for any Python module. The server will:
- Extract classes, functions, parameters, and documentation via Python introspection
- Store API data in a normalized SQLite database with full-text search
- Expose MCP tools for searching, querying, and exploring the API
- Integrate seamlessly with Claude Code

**Introspection Approach:** Uses Python's `inspect` module to analyze live objects at runtime, capturing signatures, docstrings, parameters, and inheritance relationships.

## When to Use This Skill

Use this skill when users request:
- "Create an MCP server for [Python module]"
- "Build API documentation system for [library]"
- "Set up introspection server for Python package"
- "Make [module]'s API searchable"
- Any request to create API reference tools for Python libraries

## High-Level Workflow

Creating an introspection MCP server involves four phases:

### Phase 1: Module Analysis and Planning
1. Identify target Python module
2. Verify module is importable
3. Understand module structure
4. Plan introspection strategy

### Phase 2: Introspection and Database Creation
1. Run introspection scripts
2. Create normalized SQLite database
3. Populate with API data
4. Verify database quality

### Phase 3: MCP Server Implementation
1. Design MCP tools based on use cases
2. Implement server using FastMCP
3. Create query functions
4. Add full-text search

### Phase 4: Testing and Integration
1. Test MCP server locally
2. Configure Claude Code integration
3. Validate with real queries
4. Document usage

---

## Phase 1: Module Analysis and Planning

### Step 1.1: Verify Module Availability

Check that the target module is installed and importable:

```bash
python3 -c "import MODULE_NAME; print(MODULE_NAME.__version__)"
```

If not installed, install it:

```bash
pip install MODULE_NAME
# or
uv pip install MODULE_NAME
```

### Step 1.2: Explore Module Structure

Run initial exploration:

```python
python3 -c "
import MODULE_NAME
import inspect

# Top-level attributes
print('Classes:', [n for n, o in inspect.getmembers(MODULE_NAME) if inspect.isclass(o)])
print('Functions:', [n for n, o in inspect.getmembers(MODULE_NAME) if inspect.isfunction(o)])
print('Modules:', [n for n, o in inspect.getmembers(MODULE_NAME) if inspect.ismodule(o)])
"
```

### Step 1.3: Load Reference Documentation

**Load these reference files to understand the system:**

- [📋 Database Schema Guide](references/database_schema.md) - Normalized schema patterns
- [🔍 Introspection Patterns](references/introspection_guide.md) - Python inspection techniques
- [⚡ MCP Best Practices](references/mcp_best_practices.md) - Server design principles

**For a complete walkthrough, see:**
- [📚 Complete Example: igraph](references/complete_example.md) - Full implementation reference

### Step 1.4: Plan Database Schema

Based on the module structure, determine what to capture:

**Essential Tables:**
- `modules` - Top-level modules
- `classes` - Class definitions
- `functions` - Functions and methods
- `parameters` - Function parameters with types/defaults
- `examples` - Code examples (if available)

**Optional Tables (depending on module):**
- `inheritance` - Class hierarchy
- `decorators` - Decorator information
- `constants` - Module-level constants

---

## Phase 2: Introspection and Database Creation

### Step 2.1: Run Introspection Script

Use the provided introspection utility:

```bash
python scripts/introspect.py MODULE_NAME --output data.json
```

**What this does:**
- Imports the module
- Recursively inspects all classes, functions, methods
- Captures signatures, docstrings, parameters, types
- Handles C extensions gracefully (may miss some methods)
- Outputs structured JSON

### Step 2.2: Create SQLite Database

Run the database creation script:

```bash
python scripts/create_database.py data.json --output MODULE_NAME_api.db
```

**What this creates:**
- Normalized SQLite database
- FTS5 full-text search tables
- Proper foreign key relationships
- Indexes for performance

### Step 2.3: Verify Database Quality

Check what was captured:

```bash
sqlite3 MODULE_NAME_api.db "
SELECT
    (SELECT COUNT(*) FROM modules) as modules,
    (SELECT COUNT(*) FROM classes) as classes,
    (SELECT COUNT(*) FROM functions) as functions,
    (SELECT COUNT(*) FROM parameters) as parameters;
"
```

**Quality checks:**
- Are class counts reasonable?
- Are methods captured for main classes?
- Are docstrings present?
- Are parameters captured with types?

**If data seems incomplete:**
- Check for C extension methods (may not be introspectable)
- Verify module imported correctly
- Check for dynamic attributes
- Consider manual supplementation

---

## Phase 3: MCP Server Implementation

### Step 3.1: Design MCP Tools

Based on the igraph example, design 6-8 core tools:

**Essential Tools:**
1. `search_api` - Full-text search across all documentation
2. `get_class_info` - Detailed class information
3. `get_function_info` - Detailed function/method information
4. `list_classes` - Browse available classes
5. `list_functions` - Browse available functions
6. `get_parameters` - Parameter details for a function
7. `find_examples` - Search code examples (if available)
8. `get_related` - Find related classes/functions

### Step 3.2: Generate MCP Server Scaffold

Use the scaffolding script:

```bash
python scripts/create_mcp_server.py MODULE_NAME \
    --database MODULE_NAME_api.db \
    --output mcp_server/
```

**What this creates:**
- `server.py` - FastMCP server implementation
- `queries.py` - Database query functions
- `pyproject.toml` - Project configuration
- `README.md` - Server documentation

### Step 3.3: Customize MCP Tools

Edit `mcp_server/server.py` to refine tool implementations:

**Best Practices:**
- Return markdown-formatted results
- Provide concise by default, detailed on request
- Include relevant metadata (module, class, signature)
- Handle not-found cases gracefully
- Optimize for AI consumption (high-signal, low-noise)

**Example Tool Pattern:**
```python
@mcp.tool()
async def get_class_info(
    class_name: str,
    include_methods: bool = True
) -> str:
    """
    Get detailed information about a class.

    Args:
        class_name: Name of the class
        include_methods: Include list of methods
    """
    # Query database
    # Format as markdown
    # Return high-signal information
```

### Step 3.4: Implement Query Functions

In `mcp_server/queries.py`, create efficient database queries:

```python
def search_api_fts(db_path: str, query: str, limit: int = 10) -> List[Dict]:
    """Full-text search across all API documentation"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute("""
        SELECT
            classes.name,
            classes.docstring,
            modules.name as module_name,
            fts_rank.rank
        FROM classes_fts
        JOIN classes ON classes_fts.rowid = classes.id
        JOIN modules ON classes.module_id = modules.id
        JOIN (SELECT rowid, rank FROM classes_fts WHERE classes_fts MATCH ?) fts_rank
            ON fts_rank.rowid = classes.id
        ORDER BY fts_rank.rank
        LIMIT ?
    """, (query, limit))

    return [dict(row) for row in cursor.fetchall()]
```

---

## Phase 4: Testing and Integration

### Step 4.1: Test MCP Server Locally

Use the validation script:

```bash
python scripts/validate_server.py mcp_server/server.py \
    --test-queries "search for layout" "get Graph class" "list all classes"
```

**What this checks:**
- Server starts correctly
- Tools are accessible
- Queries return results
- Error handling works
- Performance is reasonable

### Step 4.2: Configure Claude Code Integration

Add to `.mcp.json`:

```json
{
  "mcpServers": {
    "MODULE_NAME-introspection": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_server.server"],
      "cwd": "/absolute/path/to/mcp_server",
      "env": {
        "PYTHONPATH": "/absolute/path/to/mcp_server",
        "DB_PATH": "/absolute/path/to/MODULE_NAME_api.db"
      },
      "description": "MODULE_NAME API introspection - X tools for querying Y classes, Z functions"
    }
  }
}
```

Add permissions to `.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "mcp__MODULE_NAME-introspection__search_api",
      "mcp__MODULE_NAME-introspection__get_class_info",
      "mcp__MODULE_NAME-introspection__get_function_info",
      "mcp__MODULE_NAME-introspection__list_classes",
      "mcp__MODULE_NAME-introspection__list_functions",
      "mcp__MODULE_NAME-introspection__find_examples",
      "mcp__MODULE_NAME-introspection__get_parameters",
      "mcp__MODULE_NAME-introspection__get_related"
    ]
  },
  "enabledMcpjsonServers": [
    "MODULE_NAME-introspection"
  ]
}
```

### Step 4.3: Validate with Real Queries

Restart Claude Code and test the MCP tools:

```
Claude, using the MODULE_NAME-introspection MCP server,
search for functions related to "data processing"
```

```
Claude, get detailed information about the MainClass class
```

```
Claude, find examples showing how to use the transform function
```

### Step 4.4: Create Documentation

Generate user-facing documentation:

**README.md Structure:**
1. Overview - What the server provides
2. Installation - Setup instructions
3. Available Tools - List of 8 MCP tools with descriptions
4. Usage Examples - Common query patterns
5. Database Statistics - What was captured
6. Limitations - Known gaps (C extensions, etc.)

---

## Quality Checklist

### Introspection Quality
- [ ] All major classes captured
- [ ] Methods captured for classes
- [ ] Function signatures are complete
- [ ] Docstrings are preserved
- [ ] Parameters include types and defaults
- [ ] Inheritance relationships captured

### Database Quality
- [ ] Normalized schema with foreign keys
- [ ] FTS5 indexes for full-text search
- [ ] Performance indexes on common queries
- [ ] No data duplication
- [ ] Proper NULL handling

### MCP Server Quality
- [ ] 6-8 well-designed tools
- [ ] Tools enable complete workflows
- [ ] Markdown-formatted responses
- [ ] Graceful error handling
- [ ] Optimized for AI consumption
- [ ] Tool descriptions are clear
- [ ] Performance is acceptable (<1s for most queries)

### Integration Quality
- [ ] Server starts without errors
- [ ] MCP tools are accessible in Claude Code
- [ ] Permissions configured correctly
- [ ] Test queries return expected results
- [ ] Documentation is complete
- [ ] Error messages are helpful

---

## Troubleshooting

### Introspection Issues

**Problem:** C extension methods not captured
**Solution:** This is expected. C extensions hide implementation details. Document known gaps.

**Problem:** Empty docstrings
**Solution:** Some libraries lack documentation. Consider supplementing manually.

**Problem:** Dynamic attributes missing
**Solution:** Introspection captures static structure only. Document dynamic behavior separately.

### Database Issues

**Problem:** Foreign key constraint violations
**Solution:** Check insertion order. Insert modules before classes, classes before methods.

**Problem:** Full-text search not working
**Solution:** Verify FTS5 tables created correctly. Check SQLite version (3.9.0+).

**Problem:** Slow queries
**Solution:** Add indexes on frequently queried columns. Use EXPLAIN QUERY PLAN.

### MCP Server Issues

**Problem:** Server won't start
**Solution:** Check PYTHONPATH, DB_PATH environment variables. Verify database exists.

**Problem:** Tools not showing in Claude Code
**Solution:** Restart Claude Code. Check `.mcp.json` syntax. Verify permissions in settings.local.json.

**Problem:** Queries return no results
**Solution:** Check database has data. Test queries directly with sqlite3. Verify search syntax.

---

## Optimization Strategies

### For Large Modules (1000+ functions)

**Database optimizations:**
- Create covering indexes for common queries
- Use prepared statements
- Enable query result caching
- Consider connection pooling

**Search optimizations:**
- Implement relevance ranking
- Add filter options (module, class, type)
- Provide concise vs. detailed modes
- Limit default result counts

### For Complex Hierarchies

**Capture strategies:**
- Store complete inheritance chains
- Index by base classes
- Track method overrides
- Document abstract methods

**Query strategies:**
- Provide "get_subclasses" tool
- Show inherited methods
- Highlight overridden methods
- Display class hierarchy trees

---

## Example: Complete Workflow

See [references/complete_example.md](references/complete_example.md) for a complete walkthrough using igraph as the example module.

**Summary of igraph implementation:**
1. Introspected 111 classes, 878 functions
2. Created 1.59 MB SQLite database with FTS5 search
3. Implemented 8 MCP tools
4. Integrated with Claude Code
5. Successfully validated API calls in real scripts

---

## Dependencies

The provided scripts require:

```
# requirements.txt
fastmcp>=0.1.0
sqlite-utils>=3.0.0
anthropic-mcp>=0.1.0
```

Install with:
```bash
pip install -r scripts/requirements.txt
# or
uv pip install -r scripts/requirements.txt
```

---

## Next Steps After Server Creation

1. **Test with Real Use Cases**: Use the MCP server to validate actual code
2. **Gather Feedback**: See what queries are common, what's missing
3. **Iterate**: Add tools, improve search, enhance documentation
4. **Share**: Consider publishing as a Claude Code plugin
5. **Document Gaps**: Note C extension limitations and workarounds

---

## Reference Files

**Core Guides:**
- [📋 Database Schema Guide](references/database_schema.md) - Schema design patterns
- [🔍 Introspection Guide](references/introspection_guide.md) - Python inspection techniques
- [⚡ MCP Best Practices](references/mcp_best_practices.md) - Server design principles
- [📚 Complete Example: igraph](references/complete_example.md) - Full implementation walkthrough

**External Resources:**
- MCP Protocol Docs: https://modelcontextprotocol.io/llms-full.txt
- FastMCP Documentation: https://github.com/jlowin/fastmcp
- SQLite FTS5: https://www.sqlite.org/fts5.html
- Python inspect module: https://docs.python.org/3/library/inspect.html

---

## Script Reference

All scripts include `--help` documentation. Run with `--help` first:

```bash
python scripts/introspect.py --help
python scripts/create_database.py --help
python scripts/create_mcp_server.py --help
python scripts/validate_server.py --help
```

Scripts are designed to be composable:
```bash
# Complete workflow
python scripts/introspect.py MODULE_NAME --output data.json
python scripts/create_database.py data.json --output MODULE_NAME_api.db
python scripts/create_mcp_server.py MODULE_NAME --database MODULE_NAME_api.db --output mcp_server/
python scripts/validate_server.py mcp_server/server.py
```
