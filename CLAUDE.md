# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**create-introspect-mcp** is a Python toolkit for creating introspection-based MCP (Model Context Protocol) servers. It provides automated scripts that introspect any Python module and generate a complete MCP server with searchable API documentation.

The workflow transforms Python modules into MCP servers with 4 automated scripts:
1. **introspect.py** - Extracts classes, functions, methods, docstrings, and type information
2. **create_database.py** - Creates a normalized SQLite database with FTS5 full-text search
3. **create_mcp_server.py** - Generates a complete FastMCP server with 8 API exploration tools
4. **validate_server.py** - Tests the generated server with comprehensive validation

## Development Commands

### Testing
```bash
# Run all tests with coverage
python -m pytest tests/ -v --cov=scripts --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_introspect.py -v

# Run only unit tests
python -m pytest tests/ -m unit

# Run only integration tests
python -m pytest tests/ -m integration

# Run without coverage (faster)
python -m pytest tests/ -v --no-cov

# Generate HTML coverage report
python -m pytest tests/ --cov=scripts --cov-report=html
# View at htmlcov/index.html
```

### Linting & Formatting
```bash
# Format all code (auto-fix)
python -m ruff format scripts/ tests/

# Check all code (linting)
python -m ruff check scripts/ tests/

# Auto-fix linting issues
python -m ruff check scripts/ tests/ --fix

# Type checking with pyright
python -m pyright scripts/ tests/
```

### Quality Checks (All)
```bash
# Run complete quality pipeline
python -m ruff format scripts/ tests/ && \
python -m ruff check scripts/ tests/ && \
python -m pyright scripts/ tests/ && \
python -m pytest tests/ -v --cov=scripts
```

### Running Scripts
```bash
# Introspect a Python module
python scripts/introspect.py MODULE_NAME --output data.json

# Create database from introspection data
python scripts/create_database.py data.json --output MODULE_api.db

# Generate MCP server
python scripts/create_mcp_server.py MODULE_NAME --database MODULE_api.db --output mcp_server/

# Validate generated server
python scripts/validate_server.py mcp_server/server.py --verbose
```

### Publishing the Skill
```bash
# Create a clean distribution build (auto-increment build number)
python publish.py

# Create a specific build number
python publish.py --build-number 5

# Preview what would be copied (dry run)
python publish.py --dry-run

# Copy the latest build to another project
cp -r dist/build_0001/create-introspect-mcp /path/to/project/.claude/skills/
```

The publish script creates versioned builds in `dist/build_NNNN/create-introspect-mcp/` containing only the files needed for the Claude Code skill to function (excludes tests, dev config, etc.).

## Architecture Overview

### Core Scripts Architecture

The toolkit follows a **pipeline architecture** where each script is a composable stage:

**Stage 1: Introspection** (`scripts/introspect.py`)
- Uses Python's `inspect` module to analyze live module objects at runtime
- Recursively explores modules, classes, and functions
- Extracts signatures, docstrings, parameters, type hints, and inheritance
- Handles C extensions gracefully (introspection may be limited)
- Outputs structured JSON with normalized data

**Stage 2: Database Creation** (`scripts/create_database.py`)
- Parses introspection JSON and creates normalized SQLite schema
- Tables: `modules`, `classes`, `functions`, `parameters`
- Creates FTS5 (Full-Text Search) tables for all text content
- Establishes foreign key relationships and indexes
- Implements sync triggers to keep FTS tables updated

**Stage 3: Server Generation** (`scripts/create_mcp_server.py`)
- Template-based code generation for complete MCP server
- Generates 8 MCP tools: search_api, get_class_info, get_function_info, list_classes, list_functions, get_parameters, find_examples, get_related
- Creates query functions that interact with the SQLite database
- Produces pyproject.toml, README.md, and complete project structure
- Server uses `mcp.server` library (not FastMCP despite docs)

**Stage 4: Validation** (`scripts/validate_server.py`)
- Import validation (checks if server module loads)
- Database connectivity tests
- Tool accessibility verification
- Sample query execution
- Performance benchmarking
- Comprehensive test reporting

### Database Schema

The database uses a **normalized relational schema** with FTS5 for search:

```
modules (id, name, docstring, version, file_path)
  ├─> classes (id, module_id, name, docstring, base_classes, file_path, line_number)
  │     ├─> classes_fts (FTS5: name, docstring)
  │     └─> functions (id, module_id, class_id, name, docstring, signature, ...)
  │           ├─> functions_fts (FTS5: name, docstring, signature)
  │           └─> parameters (id, function_id, name, kind, annotation, default, position)
  └─> functions (module-level functions, class_id=NULL)
```

**Key Design Decisions:**
- Functions table serves both module-level functions and methods (class_id nullable)
- FTS5 tables mirror main tables for full-text search
- Foreign keys enforce referential integrity
- Sync triggers keep FTS tables updated automatically
- Indexes on name, module_id, class_id for query performance

### Generated MCP Server Architecture

Generated servers follow this structure:

```
mcp_server/
├── server.py        # Main MCP server with 8 tool implementations
├── queries.py       # Database query functions (not actually generated)
├── pyproject.toml   # Project configuration
└── README.md        # Server documentation
```

**MCP Tools Pattern:**
Each tool follows a consistent pattern:
1. Accept search/filter parameters
2. Query SQLite database (inline in server.py, not via queries.py)
3. Format results as markdown
4. Return high-signal, AI-optimized responses

**Important:** Despite references to `queries.py` in documentation, the generated server.py contains all query logic inline. There is no separate queries.py file generated.

## Important Implementation Notes

### Introspection Limitations
- **C Extensions:** Methods implemented in C may not be fully introspectable (docstrings and signatures might be missing)
- **Dynamic Attributes:** Properties generated at runtime won't be captured
- **Private Members:** By default, private members (prefixed with `_`) are excluded unless `--include-private` flag is used

### Database Considerations
- **Insertion Order:** Must insert modules → classes → functions → parameters (respects foreign keys)
- **FTS5 Requirements:** Requires SQLite 3.9.0+ with FTS5 support
- **NULL Handling:** Functions can have NULL class_id (module-level) or NULL module_id (class methods)

### Generated Server Notes
- Uses `mcp.server.Server` and `mcp.server.stdio.stdio_server`, not FastMCP
- Database path configured via environment variable `DB_PATH` or defaults to relative path
- All 8 tools are generated automatically, no manual implementation needed
- Tools return markdown-formatted strings for optimal AI consumption

### Testing Strategy
The test suite uses pytest with these patterns:
- **Fixtures** in `tests/conftest.py` provide reusable test data and temp directories
- **Markers:** `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- **Parametrization:** Tests use `@pytest.mark.parametrize` for multiple scenarios
- **Mocking:** Uses `unittest.mock` for testing without external dependencies
- **Coverage:** Target is 73%+ overall (currently achieved)

## Common Development Patterns

### Adding a New Script
1. Create script in `scripts/` with proper shebang and docstring
2. Add argparse interface with `--help` documentation
3. Implement main logic in a class with `verbose` logging
4. Add comprehensive error handling
5. Create corresponding test file in `tests/`
6. Update `pyproject.toml` if new dependencies are needed

### Modifying Database Schema
1. Update schema creation in `create_database.py:create_schema()`
2. Update FTS table creation to mirror new fields
3. Update insertion logic in corresponding methods
4. Update `create_mcp_server.py` templates if tools need new data
5. Add migration logic if database already exists (not currently supported)

### Extending Generated MCP Tools
1. Modify templates in `create_mcp_server.py` (SERVER_TEMPLATE, README_TEMPLATE, etc.)
2. Add new tool function to SERVER_TEMPLATE
3. Update README_TEMPLATE to document new tool
4. Regenerate test server and validate with `validate_server.py`

## Files and Locations

```
create-introspect-mcp/
├── scripts/                  # Core automation scripts (4 main scripts)
│   ├── __init__.py          # Package initialization
│   ├── introspect.py        # Python module introspection (459 lines)
│   ├── create_database.py   # SQLite database creation (387 lines)
│   ├── create_mcp_server.py # MCP server generation (585 lines)
│   ├── validate_server.py   # Server validation (387 lines)
│   └── requirements.txt     # Runtime dependencies
├── tests/                   # Test suite (35 tests, 100% pass rate)
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   ├── test_introspect.py
│   ├── test_create_database.py
│   ├── test_create_mcp_server.py
│   └── test_validate_server.py
├── pyproject.toml           # Project config (ruff, pyright, pytest)
├── dev_requirements.txt     # Dev dependencies
├── SKILL.md                 # Complete 4-phase workflow guide (582 lines)
└── STATUS.md                # Project status and metrics
```

## Key Quality Metrics

**Current Status (as of 2025-10-23):**
- **Tests:** 35/35 passing (100% pass rate)
- **Coverage:** 73% overall (acceptable for scripts)
- **Type Checking:** 0 errors (pyright basic mode)
- **Linting:** All checks passing (ruff)
- **Code Quality:** Production-ready

## Workflow Example

Complete end-to-end workflow for creating an MCP server:

```bash
# 1. Install a Python library you want to introspect
pip install requests

# 2. Introspect the module
python scripts/introspect.py requests --output requests_data.json

# 3. Create searchable database
python scripts/create_database.py requests_data.json --output requests_api.db

# 4. Generate MCP server
python scripts/create_mcp_server.py requests \
  --database requests_api.db \
  --output requests-mcp-server/

# 5. Validate the server
python scripts/validate_server.py requests-mcp-server/server.py --verbose

# 6. Configure Claude Code integration
# Add to .mcp.json:
{
  "mcpServers": {
    "requests-introspection": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "-m", "server"],
      "cwd": "/absolute/path/to/requests-mcp-server",
      "env": {
        "DB_PATH": "/absolute/path/to/requests_api.db"
      }
    }
  }
}
```

## Dependencies

**Runtime:**
- `mcp>=1.18.0` - MCP protocol implementation

**Development:**
- `pytest>=8.4.2` - Testing framework
- `pytest-asyncio>=1.2.0` - Async test support
- `pytest-cov>=7.0.0` - Coverage reporting
- `ruff>=0.14.1` - Linting and formatting
- `pyright>=1.1.406` - Type checking

**Generated Servers Require:**
- `mcp>=0.9.0` - MCP server library
- `sqlite3` - Built into Python
