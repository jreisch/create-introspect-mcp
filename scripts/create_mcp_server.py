#!/usr/bin/env python3
"""
MCP Server Scaffolding Tool

Generates a complete FastMCP server from an introspection database.
Creates server.py, queries.py, pyproject.toml, and README.md.

Features:
- Template-based server generation
- 8 core MCP tools for API exploration
- Query functions with proper error handling
- Project configuration files
- Documentation

Usage:
    python create_mcp_server.py MODULE_NAME --database module_api.db --output mcp_server/
    python create_mcp_server.py igraph --database igraph_api.db --output igraph-introspection/
"""

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Any

SERVER_TEMPLATE = '''#!/usr/bin/env python3
"""
{module_name} API Introspection MCP Server

Provides MCP tools for exploring the {module_name} Python library API.

Available Tools:
- search_api: Full-text search across all documentation
- get_class_info: Detailed class information with methods
- get_function_info: Detailed function/method information
- list_classes: Browse available classes
- list_functions: Browse module-level functions
- get_parameters: Parameter details for functions
- find_examples: Search code examples (if available)
- get_related: Find related classes/functions

Database: {database_path}
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Database path from environment or default
DB_PATH = os.getenv("DB_PATH", "{database_path}")

# Initialize MCP server
app = Server("{module_name}-introspection")


def get_db_connection():
    """Get database connection"""
    db_path = Path(DB_PATH)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {{db_path}}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available MCP tools"""
    return [
        types.Tool(
            name="search_api",
            description="Full-text search across all {module_name} API documentation (classes, functions, docstrings)",
            inputSchema={{
                "type": "object",
                "properties": {{
                    "query": {{"type": "string", "description": "Search query"}},
                    "limit": {{"type": "integer", "description": "Maximum results (default: 10)", "default": 10}}
                }},
                "required": ["query"]
            }}
        ),
        types.Tool(
            name="get_class_info",
            description="Get detailed information about a specific {module_name} class",
            inputSchema={{
                "type": "object",
                "properties": {{
                    "class_name": {{"type": "string", "description": "Name of the class"}},
                    "include_methods": {{"type": "boolean", "description": "Include methods list", "default": True}},
                    "include_examples": {{"type": "boolean", "description": "Include code examples", "default": True}}
                }},
                "required": ["class_name"]
            }}
        ),
        types.Tool(
            name="get_function_info",
            description="Get detailed information about a {module_name} function or method",
            inputSchema={{
                "type": "object",
                "properties": {{
                    "function_name": {{"type": "string", "description": "Function name or ClassName.method_name"}},
                    "include_parameters": {{"type": "boolean", "description": "Include parameter details", "default": True}},
                    "include_examples": {{"type": "boolean", "description": "Include code examples", "default": True}}
                }},
                "required": ["function_name"]
            }}
        ),
        types.Tool(
            name="list_classes",
            description="List all {module_name} classes with optional filtering",
            inputSchema={{
                "type": "object",
                "properties": {{
                    "module": {{"type": "string", "description": "Filter by module name"}},
                    "limit": {{"type": "integer", "description": "Maximum results", "default": 50}}
                }}
            }}
        ),
        types.Tool(
            name="list_functions",
            description="List {module_name} module-level functions (not methods)",
            inputSchema={{
                "type": "object",
                "properties": {{
                    "module": {{"type": "string", "description": "Filter by module name"}},
                    "limit": {{"type": "integer", "description": "Maximum results", "default": 50}}
                }}
            }}
        ),
        types.Tool(
            name="get_parameters",
            description="Get detailed parameter information for a function/method",
            inputSchema={{
                "type": "object",
                "properties": {{
                    "function_name": {{"type": "string", "description": "Function name or ClassName.method_name"}}
                }},
                "required": ["function_name"]
            }}
        ),
        types.Tool(
            name="find_examples",
            description="Search for code examples in {module_name} documentation",
            inputSchema={{
                "type": "object",
                "properties": {{
                    "query": {{"type": "string", "description": "Search query"}},
                    "limit": {{"type": "integer", "description": "Maximum results", "default": 10}}
                }},
                "required": ["query"]
            }}
        ),
        types.Tool(
            name="get_related",
            description="Find related classes and functions (inheritance, similar names, same module)",
            inputSchema={{
                "type": "object",
                "properties": {{
                    "entity_name": {{"type": "string", "description": "Class or function name"}},
                    "relation_types": {{"type": "string", "description": "Comma-separated: inheritance,similar,module"}}
                }},
                "required": ["entity_name"]
            }}
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[types.TextContent]:
    """Handle tool calls"""

    try:
        if name == "search_api":
            result = search_api(arguments.get("query"), arguments.get("limit", 10))
        elif name == "get_class_info":
            result = get_class_info(
                arguments.get("class_name"),
                arguments.get("include_methods", True),
                arguments.get("include_examples", True)
            )
        elif name == "get_function_info":
            result = get_function_info(
                arguments.get("function_name"),
                arguments.get("include_parameters", True),
                arguments.get("include_examples", True)
            )
        elif name == "list_classes":
            result = list_classes(
                arguments.get("module"),
                arguments.get("limit", 50)
            )
        elif name == "list_functions":
            result = list_functions(
                arguments.get("module"),
                arguments.get("limit", 50)
            )
        elif name == "get_parameters":
            result = get_parameters(arguments.get("function_name"))
        elif name == "find_examples":
            result = find_examples(
                arguments.get("query"),
                arguments.get("limit", 10)
            )
        elif name == "get_related":
            result = get_related(
                arguments.get("entity_name"),
                arguments.get("relation_types")
            )
        else:
            result = f"Unknown tool: {{name}}"

        return [types.TextContent(type="text", text=str(result))]

    except Exception as e:
        error_msg = f"Error executing {{name}}: {{str(e)}}"
        return [types.TextContent(type="text", text=error_msg)]


def search_api(query: str, limit: int = 10) -> str:
    """Full-text search across API documentation"""
    conn = get_db_connection()

    results = []

    # Search classes
    cursor = conn.execute("""
        SELECT
            c.name,
            c.full_qualified_name,
            c.docstring,
            m.name as module_name
        FROM classes_fts
        JOIN classes c ON classes_fts.rowid = c.id
        JOIN modules m ON c.module_id = m.id
        WHERE classes_fts MATCH ?
        LIMIT ?
    """, (query, limit // 2))

    for row in cursor:
        doc = row['docstring'][:200] + "..." if row['docstring'] and len(row['docstring']) > 200 else row['docstring']
        results.append(f"**Class: {{row['full_qualified_name']}}**\\nModule: {{row['module_name']}}\\n{{doc or 'No documentation'}}")

    # Search functions
    cursor = conn.execute("""
        SELECT
            f.name,
            f.full_qualified_name,
            f.signature_string,
            f.docstring,
            m.name as module_name
        FROM functions_fts
        JOIN functions f ON functions_fts.rowid = f.id
        JOIN modules m ON f.module_id = m.id
        WHERE functions_fts MATCH ?
        LIMIT ?
    """, (query, limit // 2))

    for row in cursor:
        doc = row['docstring'][:200] + "..." if row['docstring'] and len(row['docstring']) > 200 else row['docstring']
        results.append(f"**Function: {{row['full_qualified_name']}}{{row['signature_string']}}**\\nModule: {{row['module_name']}}\\n{{doc or 'No documentation'}}")

    conn.close()

    if not results:
        return f"No results found for '{{query}}'"

    return f"# Search Results for '{{query}}'\\n\\nFound {{len(results)}} results:\\n\\n" + "\\n\\n".join(results)


def get_class_info(class_name: str, include_methods: bool = True, include_examples: bool = True) -> str:
    """Get detailed class information"""
    conn = get_db_connection()

    # Get class info
    cursor = conn.execute("""
        SELECT c.*, m.name as module_name
        FROM classes c
        JOIN modules m ON c.module_id = m.id
        WHERE c.name = ? OR c.full_qualified_name = ?
    """, (class_name, class_name))

    row = cursor.fetchone()
    if not row:
        conn.close()
        return f"Class '{{class_name}}' not found"

    output = [f"# Class: {{row['name']}}\\n"]
    output.append(f"**Module**: `{{row['module_name']}}`\\n")
    output.append(f"**Qualified Name**: `{{row['full_qualified_name']}}`\\n")

    # Get inheritance
    cursor = conn.execute("""
        SELECT base_class_name
        FROM class_inheritance
        WHERE class_id = ?
    """, (row['id'],))

    bases = [r['base_class_name'] for r in cursor]
    if bases:
        output.append(f"**Inherits from**: {{', '.join(f'`{{b}}`' for b in bases)}}\\n")

    # Documentation
    if row['docstring']:
        output.append(f"## Documentation\\n\\n{{row['docstring']}}\\n")

    # Methods
    if include_methods:
        cursor = conn.execute("""
            SELECT name, signature_string
            FROM functions
            WHERE class_id = ?
            ORDER BY name
        """, (row['id'],))

        methods = cursor.fetchall()
        if methods:
            output.append(f"## Methods ({{len(methods)}})\\n")
            for method in methods:
                output.append(f"- **`{{method['name']}}{{method['signature_string']}}`**")

    conn.close()
    return "\\n".join(output)


def get_function_info(function_name: str, include_parameters: bool = True, include_examples: bool = True) -> str:
    """Get detailed function information"""
    conn = get_db_connection()

    # Handle ClassName.method_name format
    if '.' in function_name:
        class_part, method_part = function_name.rsplit('.', 1)
        cursor = conn.execute("""
            SELECT f.*, m.name as module_name, c.name as class_name
            FROM functions f
            JOIN modules m ON f.module_id = m.id
            LEFT JOIN classes c ON f.class_id = c.id
            WHERE (c.name = ? OR c.full_qualified_name = ?) AND f.name = ?
        """, (class_part, class_part, method_part))
    else:
        cursor = conn.execute("""
            SELECT f.*, m.name as module_name, c.name as class_name
            FROM functions f
            JOIN modules m ON f.module_id = m.id
            LEFT JOIN classes c ON f.class_id = c.id
            WHERE f.name = ? OR f.full_qualified_name = ?
        """, (function_name, function_name))

    row = cursor.fetchone()
    if not row:
        conn.close()
        return f"Function '{{function_name}}' not found"

    func_type = "Method" if row['class_name'] else "Function"
    output = [f"# {{func_type}}: {{row['name']}}\\n"]
    output.append(f"**Module**: `{{row['module_name']}}`\\n")

    if row['class_name']:
        output.append(f"**Class**: `{{row['class_name']}}`\\n")

    # Signature
    output.append(f"## Signature\\n\\n```python\\n{{row['signature_string']}}\\n```\\n")

    # Documentation
    if row['docstring']:
        output.append(f"## Documentation\\n\\n{{row['docstring']}}\\n")

    # Parameters
    if include_parameters:
        cursor = conn.execute("""
            SELECT name, kind, annotation, default_value
            FROM parameters
            WHERE function_id = ?
            ORDER BY position
        """, (row['id'],))

        params = cursor.fetchall()
        if params:
            output.append(f"## Parameters\\n")
            for param in params:
                param_line = f"- **`{{param['name']}}`**"
                if param['annotation']:
                    param_line += f": `{{param['annotation']}}`"
                if param['default_value']:
                    param_line += f" = `{{param['default_value']}}`"
                output.append(param_line)

    conn.close()
    return "\\n".join(output)


def list_classes(module: Optional[str] = None, limit: int = 50) -> str:
    """List classes"""
    conn = get_db_connection()

    if module:
        cursor = conn.execute("""
            SELECT c.name, c.full_qualified_name, m.name as module_name
            FROM classes c
            JOIN modules m ON c.module_id = m.id
            WHERE m.name LIKE ?
            ORDER BY c.name
            LIMIT ?
        """, (f"%{{module}}%", limit))
    else:
        cursor = conn.execute("""
            SELECT c.name, c.full_qualified_name, m.name as module_name
            FROM classes c
            JOIN modules m ON c.module_id = m.id
            ORDER BY c.name
            LIMIT ?
        """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "No classes found"

    output = [f"# Classes ({{len(rows)}})\\n"]
    for row in rows:
        output.append(f"- **`{{row['name']}}`** - `{{row['full_qualified_name']}}`")

    return "\\n".join(output)


def list_functions(module: Optional[str] = None, limit: int = 50) -> str:
    """List module-level functions"""
    conn = get_db_connection()

    if module:
        cursor = conn.execute("""
            SELECT f.name, f.full_qualified_name, f.signature_string, m.name as module_name
            FROM functions f
            JOIN modules m ON f.module_id = m.id
            WHERE f.class_id IS NULL AND m.name LIKE ?
            ORDER BY f.name
            LIMIT ?
        """, (f"%{{module}}%", limit))
    else:
        cursor = conn.execute("""
            SELECT f.name, f.full_qualified_name, f.signature_string, m.name as module_name
            FROM functions f
            JOIN modules m ON f.module_id = m.id
            WHERE f.class_id IS NULL
            ORDER BY f.name
            LIMIT ?
        """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "No functions found"

    output = [f"# Functions ({{len(rows)}})\\n"]
    for row in rows:
        output.append(f"- **`{{row['name']}}{{row['signature_string']}}`** - Module: `{{row['module_name']}}`")

    return "\\n".join(output)


def get_parameters(function_name: str) -> str:
    """Get parameter details"""
    # Reuse get_function_info logic
    return get_function_info(function_name, include_parameters=True, include_examples=False)


def find_examples(query: str, limit: int = 10) -> str:
    """Search code examples"""
    conn = get_db_connection()

    cursor = conn.execute("""
        SELECT code, description
        FROM examples
        WHERE code LIKE ? OR description LIKE ?
        LIMIT ?
    """, (f"%{{query}}%", f"%{{query}}%", limit))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return f"No examples found containing '{{query}}'"

    output = [f"# Code Examples for '{{query}}'\\n"]
    for i, row in enumerate(rows, 1):
        output.append(f"## Example {{i}}\\n")
        if row['description']:
            output.append(f"{{row['description']}}\\n")
        output.append(f"```python\\n{{row['code']}}\\n```\\n")

    return "\\n".join(output)


def get_related(entity_name: str, relation_types: Optional[str] = None) -> str:
    """Find related entities"""
    conn = get_db_connection()

    output = [f"# Related to '{{entity_name}}'\\n"]

    # Check if it's a class
    cursor = conn.execute("""
        SELECT id, name, full_qualified_name
        FROM classes
        WHERE name = ? OR full_qualified_name = ?
    """, (entity_name, entity_name))

    class_row = cursor.fetchone()

    if class_row:
        # Get subclasses (classes that inherit from this one)
        cursor = conn.execute("""
            SELECT c.name, c.full_qualified_name
            FROM classes c
            JOIN class_inheritance ci ON c.id = ci.class_id
            WHERE ci.base_class_name = ?
        """, (class_row['name'],))

        subclasses = cursor.fetchall()
        if subclasses:
            output.append(f"## Subclasses\\n")
            for row in subclasses:
                output.append(f"- `{{row['full_qualified_name']}}`")

        # Get parent classes
        cursor = conn.execute("""
            SELECT base_class_name
            FROM class_inheritance
            WHERE class_id = ?
        """, (class_row['id'],))

        parents = cursor.fetchall()
        if parents:
            output.append(f"\\n## Parent Classes\\n")
            for row in parents:
                output.append(f"- `{{row['base_class_name']}}`")

        # Get methods
        cursor = conn.execute("""
            SELECT name
            FROM functions
            WHERE class_id = ?
            LIMIT 10
        """, (class_row['id'],))

        methods = cursor.fetchall()
        if methods:
            output.append(f"\\n## Methods (first 10)\\n")
            for row in methods:
                output.append(f"- `{{row['name']}}`")

    conn.close()

    if len(output) == 1:
        return f"No related entities found for '{{entity_name}}'"

    return "\\n".join(output)


async def main():
    """Run MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
'''

PYPROJECT_TEMPLATE = """[project]
name = "{module_name}-introspection"
version = "0.1.0"
description = "MCP server for {module_name} API introspection"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "mcp>=0.9.0",
]

[project.scripts]
{module_name}-introspection = "{module_name}_introspection.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""

README_TEMPLATE = """# {module_name} API Introspection MCP Server

MCP server providing comprehensive API documentation and search capabilities for the {module_name} Python library.

## Features

- **Full-text search** across all API documentation
- **Class information** with inheritance and methods
- **Function details** with signatures and parameters
- **Browse API** - list classes and functions
- **Find examples** - search code examples
- **Related entities** - discover connections

## Statistics

- **Classes**: {class_count:,}
- **Functions**: {function_count:,}
- **Methods**: {method_count:,}
- **Parameters**: {parameter_count:,}
- **Database size**: {db_size_mb:.2f} MB

## Installation

```bash
# Install dependencies
pip install mcp

# Or with uv
uv pip install mcp
```

## Usage

### With Claude Code

Add to `.mcp.json`:

```json
{{
  "mcpServers": {{
    "{module_name}-introspection": {{
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "-m", "server"],
      "cwd": "{output_path}",
      "env": {{
        "PYTHONPATH": "{output_path}",
        "DB_PATH": "{database_path}"
      }},
      "description": "{module_name} API introspection - {tool_count} tools for querying {class_count} classes, {total_functions} functions"
    }}
  }}
}}
```

Add permissions to `.claude/settings.local.json`:

```json
{{
  "permissions": {{
    "allow": [
      "mcp__{module_name}-introspection__search_api",
      "mcp__{module_name}-introspection__get_class_info",
      "mcp__{module_name}-introspection__get_function_info",
      "mcp__{module_name}-introspection__list_classes",
      "mcp__{module_name}-introspection__list_functions",
      "mcp__{module_name}-introspection__get_parameters",
      "mcp__{module_name}-introspection__find_examples",
      "mcp__{module_name}-introspection__get_related"
    ]
  }},
  "enabledMcpjsonServers": [
    "{module_name}-introspection"
  ]
}}
```

### Manual Testing

```bash
# Run server
python server.py

# In another terminal, test with MCP client
# (requires MCP client library)
```

## Available Tools

### search_api
Full-text search across all {module_name} API documentation.

```
query: "search term"
limit: 10 (optional)
```

### get_class_info
Get detailed information about a class.

```
class_name: "ClassName"
include_methods: true (optional)
include_examples: true (optional)
```

### get_function_info
Get detailed information about a function or method.

```
function_name: "function_name" or "ClassName.method_name"
include_parameters: true (optional)
include_examples: true (optional)
```

### list_classes
List all classes with optional filtering.

```
module: "module_name" (optional)
limit: 50 (optional)
```

### list_functions
List module-level functions.

```
module: "module_name" (optional)
limit: 50 (optional)
```

### get_parameters
Get detailed parameter information.

```
function_name: "function_name" or "ClassName.method_name"
```

### find_examples
Search for code examples.

```
query: "search term"
limit: 10 (optional)
```

### get_related
Find related classes and functions.

```
entity_name: "ClassName" or "function_name"
relation_types: "inheritance,similar,module" (optional)
```

## Database Schema

The introspection database uses a normalized schema with FTS5 full-text search:

- **modules** - Module information
- **classes** - Class definitions
- **class_inheritance** - Inheritance relationships
- **functions** - Functions and methods
- **parameters** - Function parameters
- **examples** - Code examples
- **classes_fts** - Full-text search for classes
- **functions_fts** - Full-text search for functions

## Limitations

- C extension methods may have limited introspection data
- Dynamic attributes are not captured
- Code examples depend on source documentation

## License

Generated by create-introspect-mcp Agent Skill
"""


def get_database_stats(db_path: str) -> dict[str, Any]:
    """Get statistics from database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM classes")
    class_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM functions WHERE class_id IS NULL")
    function_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM functions WHERE class_id IS NOT NULL")
    method_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM parameters")
    parameter_count = cursor.fetchone()[0]

    conn.close()

    db_size_mb = Path(db_path).stat().st_size / (1024 * 1024)

    return {
        "class_count": class_count,
        "function_count": function_count,
        "method_count": method_count,
        "parameter_count": parameter_count,
        "total_functions": function_count + method_count,
        "db_size_mb": db_size_mb,
        "tool_count": 8,
    }


def create_mcp_server(module_name: str, database_path: str, output_dir: str):
    """Create MCP server scaffold"""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Resolve absolute paths
    database_path = str(Path(database_path).resolve())
    output_abs = str(output_path.resolve())

    # Get database statistics
    print(f"Reading database statistics from: {database_path}")
    stats = get_database_stats(database_path)

    # Create server.py
    print("Creating server.py...")
    server_content = SERVER_TEMPLATE.format(module_name=module_name, database_path=database_path)

    server_path = output_path / "server.py"
    server_path.write_text(server_content)
    server_path.chmod(0o755)  # Make executable

    # Create pyproject.toml
    print("Creating pyproject.toml...")
    pyproject_content = PYPROJECT_TEMPLATE.format(module_name=module_name)
    (output_path / "pyproject.toml").write_text(pyproject_content)

    # Create README.md
    print("Creating README.md...")
    readme_content = README_TEMPLATE.format(
        module_name=module_name, output_path=output_abs, database_path=database_path, **stats
    )
    (output_path / "README.md").write_text(readme_content)

    # Print summary
    print("\n" + "=" * 60)
    print("MCP SERVER CREATED SUCCESSFULLY")
    print("=" * 60)
    print(f"Location: {output_abs}")
    print("\nFiles created:")
    print("  - server.py (FastMCP server with 8 tools)")
    print("  - pyproject.toml (Project configuration)")
    print("  - README.md (Documentation)")
    print(f"\nDatabase: {database_path}")
    print(f"  - Classes: {stats['class_count']:,}")
    print(f"  - Functions: {stats['function_count']:,}")
    print(f"  - Methods: {stats['method_count']:,}")
    print(f"  - Parameters: {stats['parameter_count']:,}")
    print(f"  - Size: {stats['db_size_mb']:.2f} MB")
    print("\nNext steps:")
    print(f"  1. Test the server: python {output_abs}/server.py")
    print("  2. Add to .mcp.json (see README.md)")
    print("  3. Restart Claude Code")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Generate FastMCP server from introspection database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("module_name", help="Name of the Python module")
    parser.add_argument("--database", "-d", required=True, help="Path to introspection database")
    parser.add_argument("--output", "-o", required=True, help="Output directory for MCP server")

    args = parser.parse_args()

    # Validate database exists
    db_path = Path(args.database)
    if not db_path.exists():
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    # Create MCP server
    create_mcp_server(args.module_name, str(db_path), args.output)


if __name__ == "__main__":
    main()
