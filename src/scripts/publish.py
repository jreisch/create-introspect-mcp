#!/usr/bin/env python3
"""
Publish/Distribution Script for MCP Introspection Servers

Creates a numbered, portable build that can be installed into any project.

Usage:
    python publish.py --server-dir requests_mcp_server --database requests_api.db --module-name requests
    python publish.py --server-dir httpx_mcp_server --database httpx_api.db --module-name httpx --build-number 2

Directory Structure Created:
    dist/build_001/requests-introspection/
    ├── .mcp.json                          # Project-level MCP configuration
    └── .claude/
        ├── settings.local.json            # Permissions configuration
        └── mcp/
            └── requests-introspection/    # The actual MCP server
                ├── README.md
                ├── server.py
                ├── requests_api.db
                └── requirements.txt

Installation:
    1. Copy contents to target project root
    2. Restart Claude Code
    3. MCP server is automatically available

Features:
    - Auto-incrementing build numbers
    - Relative paths (no hardcoded absolute paths)
    - Complete permissions list
    - Ready to copy-paste into any project
"""

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


class MCPPublisher:
    """Publishes MCP introspection server as distributable package"""

    def __init__(
        self,
        server_dir: Path,
        database_path: Path,
        module_name: str,
        output_dir: Path,
        build_number: int | None = None,
    ):
        self.server_dir = server_dir
        self.database_path = database_path
        self.module_name = module_name
        self.output_dir = output_dir
        self.mcp_name = f"{module_name}-introspection"

        # Determine build number
        if build_number is None:
            self.build_number = self._get_next_build_number()
        else:
            self.build_number = build_number

        self.build_dir = output_dir / f"build_{self.build_number:03d}" / self.mcp_name

    def _get_next_build_number(self) -> int:
        """Find next available build number"""
        if not self.output_dir.exists():
            return 1

        existing_builds = [
            d for d in self.output_dir.iterdir() if d.is_dir() and d.name.startswith("build_")
        ]

        if not existing_builds:
            return 1

        # Extract numbers from build_001, build_002, etc.
        numbers = []
        for build_dir in existing_builds:
            try:
                num_str = build_dir.name.replace("build_", "")
                numbers.append(int(num_str))
            except ValueError:
                continue

        return max(numbers) + 1 if numbers else 1

    def get_database_stats(self) -> dict:
        """Get statistics from database"""
        if not self.database_path.exists():
            return {}

        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        stats = {}

        try:
            cursor.execute("SELECT COUNT(*) FROM modules")
            stats["modules"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM classes")
            stats["classes"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM functions WHERE class_id IS NULL")
            stats["functions"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM functions WHERE class_id IS NOT NULL")
            stats["methods"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM parameters")
            stats["parameters"] = cursor.fetchone()[0]

            # Check if examples exist
            try:
                cursor.execute("SELECT COUNT(*) FROM examples")
                stats["examples"] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                stats["examples"] = 0

        except Exception as e:
            print(f"Warning: Could not read database stats: {e}", file=sys.stderr)

        conn.close()
        return stats

    def create_mcp_json(self) -> dict:
        """Create .mcp.json configuration"""
        config = {
            "mcpServers": {
                self.mcp_name: {
                    "type": "stdio",
                    "command": "uv",
                    "args": ["run", "python", "server.py"],
                    "cwd": f".claude/mcp/{self.mcp_name}",
                    "env": {
                        "PYTHONPATH": f".claude/mcp/{self.mcp_name}",
                        "DB_PATH": f".claude/mcp/{self.mcp_name}/{self.database_path.name}",
                    },
                    "description": f"{self.module_name} API introspection - 8 tools for searching classes, functions, and API documentation",
                }
            }
        }
        return config

    def create_settings_json(self) -> dict:
        """Create .claude/settings.local.json configuration"""

        # All 8 MCP tools for introspection server
        tools = [
            "search_api",
            "get_class_info",
            "get_function_info",
            "list_classes",
            "list_functions",
            "get_parameters",
            "find_examples",
            "get_related",
        ]

        permissions = [f"mcp__{self.mcp_name}__{tool}" for tool in tools]

        settings = {
            "permissions": {"allow": permissions, "deny": [], "ask": []},
            "enabledMcpjsonServers": [self.mcp_name],
        }

        return settings

    def create_readme(self, stats: dict) -> str:
        """Create README for the distribution"""

        total_functions = stats.get("functions", 0) + stats.get("methods", 0)

        readme = f"""# {self.module_name} MCP Introspection Server

Build: {self.build_number:03d}
Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overview

This is a portable MCP (Model Context Protocol) introspection server for the Python `{self.module_name}` library. It provides 8 tools for searching and exploring the {self.module_name} API through Claude Code.

## Statistics

- **Modules**: {stats.get("modules", "N/A")}
- **Classes**: {stats.get("classes", "N/A")}
- **Functions**: {stats.get("functions", "N/A")}
- **Methods**: {stats.get("methods", "N/A")}
- **Total Functions**: {total_functions}
- **Parameters**: {stats.get("parameters", "N/A")}
- **Examples**: {stats.get("examples", 0)}

## Installation

### Quick Install

1. Copy the entire contents of this distribution to your project root:
   ```bash
   # From the distribution directory
   cp -r .mcp.json .claude /path/to/your/project/
   ```

2. Restart Claude Code

3. The MCP server will be automatically available!

### Manual Install

If you already have `.mcp.json` or `.claude/settings.local.json`:

1. **Copy the MCP server directory:**
   ```bash
   mkdir -p /path/to/your/project/.claude/mcp/
   cp -r .claude/mcp/{self.mcp_name} /path/to/your/project/.claude/mcp/
   ```

2. **Merge .mcp.json contents:**
   - Add the `{self.mcp_name}` server configuration from this `.mcp.json` to your project's `.mcp.json`

3. **Merge .claude/settings.local.json contents:**
   - Add the permissions from this `settings.local.json` to your project's settings
   - Add `"{self.mcp_name}"` to `enabledMcpjsonServers` array

4. **Restart Claude Code**

## Available Tools

This MCP server provides 8 tools:

1. **search_api** - Full-text search across all {self.module_name} API documentation
2. **get_class_info** - Detailed information about a specific class
3. **get_function_info** - Detailed information about functions/methods
4. **list_classes** - Browse all available classes
5. **list_functions** - Browse module-level functions
6. **get_parameters** - Parameter details for any function/method
7. **find_examples** - Search code examples (if available)
8. **get_related** - Find related classes and functions

## Usage Examples

Once installed, you can use the MCP server in Claude Code:

```
"Search for authentication classes in {self.module_name}"

"Get detailed info about the Session class"

"List all exception classes in {self.module_name}"

"Show me parameters for the {self.module_name}.get function"

"Find examples of using {self.module_name} for authentication"
```

## Configuration Details

### MCP Server Configuration (from .mcp.json)

```json
{{
  "mcpServers": {{
    "{self.mcp_name}": {{
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "server.py"],
      "cwd": ".claude/mcp/{self.mcp_name}",
      "env": {{
        "PYTHONPATH": ".claude/mcp/{self.mcp_name}",
        "DB_PATH": ".claude/mcp/{self.mcp_name}/{self.database_path.name}"
      }},
      "description": "{self.module_name} API introspection server"
    }}
  }}
}}
```

### Required Permissions (from .claude/settings.local.json)

The following permissions are required:

```json
{{
  "permissions": {{
    "allow": [
      "mcp__{self.mcp_name}__search_api",
      "mcp__{self.mcp_name}__get_class_info",
      "mcp__{self.mcp_name}__get_function_info",
      "mcp__{self.mcp_name}__list_classes",
      "mcp__{self.mcp_name}__list_functions",
      "mcp__{self.mcp_name}__get_parameters",
      "mcp__{self.mcp_name}__find_examples",
      "mcp__{self.mcp_name}__get_related"
    ]
  }},
  "enabledMcpjsonServers": ["{self.mcp_name}"]
}}
```

## Requirements

- Python 3.10+
- `uv` package manager (or modify .mcp.json to use `python` directly)
- Claude Code

## Database

The introspection database (`{self.database_path.name}`) uses:
- Normalized SQLite schema
- FTS5 full-text search
- Complete API metadata with signatures, parameters, and docstrings

## Troubleshooting

### Server Not Showing Up

1. Check `.mcp.json` syntax is valid JSON
2. Verify paths in `.mcp.json` are correct
3. Restart Claude Code
4. Check Claude Code logs for errors

### Permission Errors

Make sure all 8 tool permissions are in `.claude/settings.local.json`:
- `mcp__{self.mcp_name}__*` for all 8 tools

### Database Not Found

Verify `DB_PATH` in `.mcp.json` points to:
`.claude/mcp/{self.mcp_name}/{self.database_path.name}`

## Support

This MCP server was generated using the `create-introspect-mcp` skill.

For issues or questions:
- Check Claude Code documentation
- Verify Python {self.module_name} library is installed in your environment
- Ensure database file is not corrupted

## License

This distribution includes:
- MCP server implementation (server.py)
- Introspection database ({self.database_path.name})
- Configuration files

The introspected {self.module_name} library is subject to its own license.
"""
        return readme

    def create_requirements_txt(self) -> str:
        """Create requirements.txt for the server"""
        requirements = f"""# MCP Introspection Server Requirements
# For {self.module_name} API introspection

mcp>=1.0.0
{self.module_name}>=2.0.0

# Optional: For better performance
# sqlite-utils>=3.0.0
"""
        return requirements

    def publish(self):
        """Create the distribution package"""

        print(f"\n{'=' * 70}")
        print(f"Publishing MCP Server: {self.mcp_name}")
        print(f"Build Number: {self.build_number:03d}")
        print(f"{'=' * 70}\n")

        # Validate inputs
        if not self.server_dir.exists():
            print(f"ERROR: Server directory not found: {self.server_dir}", file=sys.stderr)
            sys.exit(1)

        if not self.database_path.exists():
            print(f"ERROR: Database not found: {self.database_path}", file=sys.stderr)
            sys.exit(1)

        server_py = self.server_dir / "server.py"
        if not server_py.exists():
            print(f"ERROR: server.py not found in {self.server_dir}", file=sys.stderr)
            sys.exit(1)

        # Get database statistics
        print("Reading database statistics...")
        stats = self.get_database_stats()
        print(f"  Modules: {stats.get('modules', 'N/A')}")
        print(f"  Classes: {stats.get('classes', 'N/A')}")
        print(f"  Functions: {stats.get('functions', 0)} + {stats.get('methods', 0)} methods")
        print(f"  Parameters: {stats.get('parameters', 'N/A')}")

        # Create build directory structure
        print(f"\nCreating build directory: {self.build_dir}")
        self.build_dir.mkdir(parents=True, exist_ok=True)

        # Create .claude/mcp/<mcp-name> structure
        mcp_server_dir = self.build_dir / ".claude" / "mcp" / self.mcp_name
        mcp_server_dir.mkdir(parents=True, exist_ok=True)

        # Copy server files
        print(f"\nCopying server files to {mcp_server_dir.relative_to(self.build_dir)}...")
        shutil.copy2(server_py, mcp_server_dir / "server.py")
        print("  ✓ server.py")

        # Copy database
        shutil.copy2(self.database_path, mcp_server_dir / self.database_path.name)
        db_size = self.database_path.stat().st_size / 1024 / 1024
        print(f"  ✓ {self.database_path.name} ({db_size:.2f} MB)")

        # Create README
        readme_content = self.create_readme(stats)
        (mcp_server_dir / "README.md").write_text(readme_content)
        print("  ✓ README.md")

        # Create requirements.txt
        requirements_content = self.create_requirements_txt()
        (mcp_server_dir / "requirements.txt").write_text(requirements_content)
        print("  ✓ requirements.txt")

        # Create .mcp.json at root of build
        print("\nCreating configuration files at build root...")
        mcp_config = self.create_mcp_json()
        (self.build_dir / ".mcp.json").write_text(json.dumps(mcp_config, indent=2))
        print("  ✓ .mcp.json")

        # Create .claude/settings.local.json
        settings_config = self.create_settings_json()
        claude_dir = self.build_dir / ".claude"
        claude_dir.mkdir(exist_ok=True)
        (claude_dir / "settings.local.json").write_text(json.dumps(settings_config, indent=2))
        print("  ✓ .claude/settings.local.json")

        # Create installation README at build root
        install_readme = f"""# {self.mcp_name} - Build {self.build_number:03d}

## Quick Install

Copy entire contents to your project root:

```bash
cp -r .mcp.json .claude /path/to/your/project/
```

Then restart Claude Code.

## What's Included

- `.mcp.json` - MCP server configuration
- `.claude/settings.local.json` - Permissions configuration
- `.claude/mcp/{self.mcp_name}/` - The MCP server and database

## Full Documentation

See `.claude/mcp/{self.mcp_name}/README.md` for complete documentation.

## Build Info

- Module: {self.module_name}
- Build: {self.build_number:03d}
- Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- Classes: {stats.get("classes", "N/A")}
- Functions: {stats.get("functions", 0) + stats.get("methods", 0)}
"""
        (self.build_dir / "README.md").write_text(install_readme)
        print("  ✓ README.md (installation guide)")

        # Print summary
        print(f"\n{'=' * 70}")
        print(f"SUCCESS! Build {self.build_number:03d} Published")
        print(f"{'=' * 70}")
        print(f"\nLocation: {self.build_dir}")
        print("\nDirectory structure:")
        print(f"  {self.build_dir.name}/")
        print("  ├── README.md                      (installation instructions)")
        print("  ├── .mcp.json                      (MCP server config)")
        print("  └── .claude/")
        print("      ├── settings.local.json        (permissions)")
        print("      └── mcp/")
        print(f"          └── {self.mcp_name}/")
        print("              ├── README.md           (full documentation)")
        print("              ├── server.py           (MCP server)")
        print(f"              ├── {self.database_path.name}")
        print("              └── requirements.txt")

        print("\nTo install in a project:")
        print(f"  cd {self.build_dir}")
        print("  cp -r .mcp.json .claude /path/to/your/project/")
        print("  # Then restart Claude Code")

        print("\nTo create a tarball:")
        print(f"  cd {self.output_dir}")
        print(
            f"  tar -czf {self.mcp_name}-build{self.build_number:03d}.tar.gz build_{self.build_number:03d}"
        )

        return self.build_dir


def main():
    parser = argparse.ArgumentParser(
        description="Publish MCP introspection server as distributable package",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python publish.py --server-dir requests_mcp_server --database requests_api.db --module-name requests

  python publish.py --server-dir httpx_mcp_server --database httpx_api.db --module-name httpx --build-number 2

  python publish.py --server-dir requests_mcp_server --database requests_api.db --module-name requests --output dist

Output Structure:
  dist/build_001/requests-introspection/
  ├── README.md                          # Installation instructions
  ├── .mcp.json                          # MCP configuration
  └── .claude/
      ├── settings.local.json            # Permissions
      └── mcp/
          └── requests-introspection/    # The actual server
              ├── README.md
              ├── server.py
              ├── requests_api.db
              └── requirements.txt
""",
    )

    parser.add_argument(
        "--server-dir",
        required=True,
        type=Path,
        help="Path to MCP server directory (e.g., requests_mcp_server)",
    )
    parser.add_argument(
        "--database", required=True, type=Path, help="Path to database file (e.g., requests_api.db)"
    )
    parser.add_argument(
        "--module-name", required=True, help="Python module name (e.g., requests, httpx)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dist"),
        help="Output directory for builds (default: dist)",
    )
    parser.add_argument(
        "--build-number", type=int, help="Specific build number (auto-increments if not specified)"
    )

    args = parser.parse_args()

    # Create publisher and publish
    publisher = MCPPublisher(
        server_dir=args.server_dir,
        database_path=args.database,
        module_name=args.module_name,
        output_dir=args.output,
        build_number=args.build_number,
    )

    publisher.publish()


if __name__ == "__main__":
    main()
