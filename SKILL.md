---
name: create-introspect-mcp
description: Guide for creating introspection-based MCP servers that provide API documentation and search capabilities for any Python module. Use when building MCP servers for Python library documentation, API reference systems, or when users request "create an MCP server for [module name]" or "build introspection server for Python library".
---

# Create Introspection MCP Server

Create high-quality MCP servers that introspect Python modules and provide comprehensive API documentation search capabilities through the Model Context Protocol.

## Overview

This skill guides you through creating an introspection-based MCP server for any Python module. The server will:
- Extract classes, functions, parameters, and documentation via Python introspection
- Store API data in a normalized SQLite database with full-text search (includes root_module support)
- Expose 8 MCP tools for searching, querying, and exploring the API
- Package as distributable with auto-versioning
- Integrate seamlessly with Claude Code

**Introspection Approach:** Uses Python's `inspect` module to analyze live objects at runtime, capturing signatures, docstrings, parameters, and inheritance relationships.

**NEW: Publishing System** - Automatically packages servers as portable, ready-to-install distributions with configuration files and documentation.

## When to Use This Skill

Use this skill when users request:
- "Create an MCP server for [Python module]"
- "Build API documentation system for [library]"
- "Set up introspection server for Python package"
- "Make [module]'s API searchable"
- "Package/publish an MCP server for distribution"
- "Create shareable MCP server for [library]"
- Any request to create API reference tools for Python libraries

## Quick Start (Recommended)

For most users, use the **autonomous workflow**:

```bash
# Step 1: Create MCP server (fully autonomous)
python .claude/skills/create-introspect-mcp/scripts/create_full_mcp_server.py MODULE_NAME

# Step 2: Generate examples (recommended for best usability)
# See Phase 4 for detailed prompts to generate 500-1000 examples

# Step 3: Publish as distributable (fully autonomous)
python .claude/skills/create-introspect-mcp/scripts/publish.py \
    --server-dir MODULE_NAME_mcp_server \
    --database MODULE_NAME_api.db \
    --module-name MODULE_NAME

# Step 4: Install in project
cd dist/build_001/MODULE_NAME-introspection
cp -r .mcp.json .claude /path/to/your/project/

# Step 5: Restart Claude Code
```

**Example with requests module:**
```bash
# Complete workflow with example generation:

# 1. Create MCP server
python .claude/skills/create-introspect-mcp/scripts/create_full_mcp_server.py requests

# 2. Generate examples (see Phase 4 for detailed prompts)
#    - Phase 4.1: 100 use-case examples via custom script
#    - Phase 4.2: Systematic coverage via 10 parallel agents

# 3. Publish distributable
python .claude/skills/create-introspect-mcp/scripts/publish.py \
    --server-dir requests_mcp_server \
    --database requests_api.db \
    --module-name requests

# 4. Install
cd dist/build_001/requests-introspection
cp -r .mcp.json .claude ~/my-project/

# Restart Claude Code → Done!
```

Continue reading for detailed phase-by-phase instructions.

## High-Level Workflow

Creating an introspection MCP server involves six phases:

### Phase 1: Module Analysis and Planning
1. Identify target Python module
2. Verify module is importable
3. Understand module structure
4. Plan introspection strategy

### Phase 2: Introspection and Database Creation
1. Run introspection scripts
2. Create normalized SQLite database (with root_module support)
3. Populate with API data
4. Verify database quality

### Phase 3: MCP Server Implementation
1. Design MCP tools based on use cases
2. Implement server using MCP protocol
3. Create query functions
4. Add full-text search

### Phase 4: Example Generation (NEW!)
1. Generate top use-case examples
2. Achieve systematic 100% API coverage
3. Verify example quality
4. Integrate examples with MCP server

### Phase 5: Publishing and Distribution
1. Package server as distributable
2. Generate configuration files
3. Create installation documentation
4. Version with build numbers

### Phase 6: Testing and Integration
1. Test MCP server locally
2. Install in target project
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

## Phase 4: Example Generation

**IMPORTANT: This phase dramatically improves MCP server usability by adding 500-1000 practical code examples.**

### Overview

Two-phase approach to populate the database with comprehensive, verified code examples:
- **Phase 4.1**: Top 100 use-case examples (common patterns)
- **Phase 4.2**: Systematic 100% API coverage (2-3 examples per entity)

### Step 4.1: Generate Top Use-Case Examples

**Objective**: Create 100 practical examples covering the most common usage patterns.

**Prompt Template for Claude:**

```
Using the {module_name}-introspection MCP server, write the top 100 ways that the {module_name} module is used by developers in Python code.

1. First, use the MCP server to explore the API:
   - search_api for common patterns
   - list_functions to see available functions
   - list_classes to see available classes
   - get_function_info and get_class_info for details

2. Organize examples into 8-10 logical categories based on the module's purpose

3. For each example, provide:
   - A clear description (what it demonstrates)
   - 2-5 lines of practical, runnable code
   - Association with specific function or class name

4. Verify each example's correctness using the MCP server

After generating the list, write a Python script to add these 100 examples to the database. The script should:
- Look up function_id or class_id from the database
- Insert into examples table with proper foreign keys
- Handle both function and class linkages

Database schema for examples table:
- code (TEXT NOT NULL)
- description (TEXT)
- function_id (INTEGER, nullable)
- class_id (INTEGER, nullable)

IMPORTANT: For FUNCTIONS, set function_id and leave class_id NULL. For CLASSES, set class_id and leave function_id NULL.
```

**Expected Result**: 100 curated examples organized by use case, immediately useful for common scenarios.

### Step 4.2: Systematic 100% API Coverage

**Objective**: Ensure every function and class has 2-3 specific code examples.

**Step 4.2.1: Divide Entities into Groups**

```bash
# Export and divide all entities
python .claude/skills/create-introspect-mcp/scripts/divide_entities.py \
    MODULE_NAME_api.db \
    --groups 10 \
    --output-dir /tmp
```

This creates 10 files: `/tmp/entity_group_1.json` through `/tmp/entity_group_10.json`

**Step 4.2.2: Launch Parallel Agents**

**Orchestration Prompt for Claude:**

```
Using HAIKU MODEL subagents in parallel, systematically create code examples for every function and class in the {module_name} API database.

Your job as orchestrator:
1. Verify entity groups exist at /tmp/entity_group_*.json (1-10)
2. Launch 10 agents concurrently using the prompt template below
3. Wait for all agents to complete
4. Verify results with: python .claude/skills/create-introspect-mcp/scripts/verify_coverage.py {database}.db

Agent Prompt Template:
---
You are agent #{N} of 10 working in parallel to add code examples to the {module_name} API database at {database_path}.

Your task:
1. Read your assigned entities from /tmp/entity_group_{N}.json
2. For EACH entity:
   a. Use {module_name}-introspection MCP server to get entity info:
      - For FUNCTION entities: get_function_info(function_name="...", include_parameters=True)
      - For CLASS entities: get_class_info(class_name="...", include_methods=True)
   b. Create 2-3 practical, working code examples demonstrating usage
   c. Verify examples are correct and realistic
   d. Insert into database:
      INSERT INTO examples (code, description, function_id, class_id)
      VALUES (?, ?, ?, ?)

Database linkage rules:
- For FUNCTION entities: Set function_id=entity.id, leave class_id=NULL
- For CLASS entities: Set class_id=entity.id, leave function_id=NULL
- Each example: 2-5 lines of concise, practical code
- Include clear description for each example

Work systematically through ALL entities in your group. Report:
- Total entities processed
- Total examples added
- Any entities skipped with reasons
---

Launch all 10 agents in a single message using multiple Task tool calls.
```

**Expected Result**: 500-600 entity-specific examples achieving 100% API coverage.

### Step 4.3: Verify Example Coverage

```bash
# Check coverage statistics
python .claude/skills/create-introspect-mcp/scripts/verify_coverage.py MODULE_NAME_api.db
```

**Expected Output:**
```
======================================================================
Example Coverage Report
======================================================================

Total Examples: 658

Function Coverage: 177/177 (100.0%)
  Avg examples per function: 2.84

Class Coverage: 44/44 (100.0%)
  Avg examples per class: 3.55

✓ No orphaned examples

======================================================================
Overall Coverage: 221/221 entities (100.0%)
✓ 100% API COVERAGE ACHIEVED!
======================================================================
```

### Step 4.4: Quality Checklist

- [ ] Phase 4.1: 80-100 use-case examples added
- [ ] Phase 4.2: All entities have 2-3 examples
- [ ] All examples are 2-5 lines of practical code
- [ ] Each example has clear description
- [ ] Examples verified against MCP server
- [ ] Proper function_id/class_id linkage
- [ ] No orphaned examples (both IDs NULL)
- [ ] find_examples MCP tool returns results

### Benefits of This Approach

1. **MCP-First**: Uses introspection server as source of truth
2. **Two-Phase Strategy**: Common patterns first, then completeness
3. **Parallel Processing**: 10x speedup with concurrent agents
4. **High Quality**: Verified, practical, documented examples
5. **Immediate Usability**: Examples searchable via find_examples tool
6. **Replicable**: Works for any Python module with introspection server

### Time Investment

- Phase 4.1: Manual curation + script creation (~1-2 hours)
- Phase 4.2: Entity division + parallel execution (~1 hour)
- **Total: ~2-3 hours for complete example coverage**

---

## Phase 5: Publishing and Distribution

### Step 5.1: Publish as Distributable Package

**IMPORTANT: Always publish before sharing or installing in other projects**

Use the publish script to create a portable, ready-to-install package:

```bash
python .claude/skills/create-introspect-mcp/scripts/publish.py \
    --server-dir MODULE_NAME_mcp_server \
    --database MODULE_NAME_api.db \
    --module-name MODULE_NAME
```

**Example for requests module:**
```bash
python .claude/skills/create-introspect-mcp/scripts/publish.py \
    --server-dir requests_mcp_server \
    --database requests_api.db \
    --module-name requests
```

**What this creates:**
```
dist/build_001/requests-introspection/
├── .mcp.json                          # Ready-to-use MCP config
├── README.md                          # Installation instructions
└── .claude/
    ├── settings.local.json            # Pre-configured permissions
    └── mcp/
        └── requests-introspection/    # Complete MCP server
            ├── README.md              # Full documentation
            ├── server.py              # MCP server
            ├── requests_api.db        # Database (0.28 MB)
            └── requirements.txt       # Dependencies
```

**Key Features:**
- ✓ Auto-incrementing build numbers (build_001, build_002, ...)
- ✓ Relative paths (works anywhere, no hardcoding)
- ✓ Complete configuration files generated
- ✓ Full documentation included
- ✓ Database statistics extracted

**Output:**
```
======================================================================
SUCCESS! Build 001 Published
======================================================================

Location: dist/build_001/requests-introspection

To install in a project:
  cd dist/build_001/requests-introspection
  cp -r .mcp.json .claude /path/to/your/project/
  # Then restart Claude Code
```

### Step 5.2: Distribution Options

**Option A: Local Install**
```bash
cd dist/build_001/requests-introspection
cp -r .mcp.json .claude /path/to/your/project/
```

**Option B: Create Tarball**
```bash
cd dist
tar -czf requests-introspection-v001.tar.gz build_001
# Share this tarball
```

**Option C: Git Repository**
```bash
cd dist/build_001/requests-introspection
git init && git add . && git commit -m "Initial release"
git remote add origin <repo-url>
git push -u origin main
```

---

## Phase 6: Testing and Integration

### Step 6.1: Install Published Build

**From Phase 5, you now have a published build. Install it:**

```bash
# Navigate to published build
cd dist/build_001/MODULE_NAME-introspection

# Copy to target project (simple installation)
cp -r .mcp.json .claude /path/to/your/project/
```

**That's it! No manual configuration needed.**

### Step 6.2: Restart Claude Code

Restart Claude Code to load the new MCP server.

### Step 6.3: Validate with Real Queries

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

### Step 6.4: Documentation

The publish script automatically creates:
- Installation README at build root
- Complete documentation in server directory
- All 8 MCP tools described
- Usage examples included
- Database statistics shown

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
