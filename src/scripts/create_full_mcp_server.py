#!/usr/bin/env python3
"""
Complete MCP Server Creation Workflow

Runs all steps: introspection → database → server → validation

Usage:
    python create_full_mcp_server.py MODULE_NAME
    python create_full_mcp_server.py requests
    python create_full_mcp_server.py httpx --max-depth 3

This script:
1. Introspects the Python module
2. Creates SQLite database with root_module support
3. Generates MCP server with 8 tools
4. Creates configuration file templates
5. Provides next steps for Claude Code integration

Output:
    - MODULE_NAME_introspection.json (introspection data)
    - MODULE_NAME_api.db (SQLite database)
    - MODULE_NAME_mcp_server/ (MCP server directory)
    - mcp.json.template (configuration template)
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_phase(phase_name: str, cmd: list[str], cwd: Path | None = None):
    """Run a workflow phase with logging"""
    print(f"\n{'=' * 70}")
    print(f"PHASE: {phase_name}")
    print(f"{'=' * 70}")
    print(f"Running: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=cwd)

    if result.returncode != 0:
        print(f"\n!!! PHASE FAILED: {phase_name} !!!", file=sys.stderr)
        sys.exit(1)

    print(f"\n✓ {phase_name} completed successfully\n")


def detect_environment():
    """Detect which Python runner to use"""
    cwd = Path.cwd()

    # Check for uv
    if (cwd / "uv.lock").exists():
        return ["uv", "run", "--no-project", "python"]

    # Check for poetry
    if (cwd / "poetry.lock").exists():
        return ["poetry", "run", "python"]

    # Check for pipenv
    if (cwd / "Pipfile").exists():
        return ["pipenv", "run", "python"]

    # Default to system python
    return ["python"]


def create_mcp_config_template(module_name: str, server_dir: Path, api_db: Path):
    """Create .mcp.json template"""
    config = {
        "mcpServers": {
            f"{module_name}-introspection": {
                "type": "stdio",
                "command": "uv",
                "args": ["run", "--no-project", "python", "server.py"],
                "cwd": str(server_dir.absolute()),
                "env": {
                    "PYTHONPATH": str(server_dir.absolute()),
                    "DB_PATH": str(api_db.absolute()),
                },
                "description": f"{module_name} API introspection - 8 tools for searching API documentation",
            }
        }
    }

    settings = {
        "permissions": {
            "allow": [
                f"mcp__{module_name}-introspection__search_api",
                f"mcp__{module_name}-introspection__get_class_info",
                f"mcp__{module_name}-introspection__get_function_info",
                f"mcp__{module_name}-introspection__list_classes",
                f"mcp__{module_name}-introspection__list_functions",
                f"mcp__{module_name}-introspection__get_parameters",
                f"mcp__{module_name}-introspection__find_examples",
                f"mcp__{module_name}-introspection__get_related",
            ]
        },
        "enabledMcpjsonServers": [f"{module_name}-introspection"],
    }

    # Save templates
    mcp_template = server_dir / "mcp.json.template"
    settings_template = server_dir / "settings.local.json.template"

    with open(mcp_template, "w") as f:
        json.dump(config, f, indent=2)

    with open(settings_template, "w") as f:
        json.dump(settings, f, indent=2)

    return mcp_template, settings_template


def main():
    parser = argparse.ArgumentParser(
        description="Create complete MCP introspection server (all phases)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_full_mcp_server.py requests
  python create_full_mcp_server.py httpx --max-depth 3
  python create_full_mcp_server.py pandas --max-depth 2

Output files:
  - MODULE_NAME_introspection.json (raw introspection data)
  - MODULE_NAME_api.db (SQLite database with FTS5 search)
  - MODULE_NAME_mcp_server/ (complete MCP server)
  - MODULE_NAME_mcp_server/mcp.json.template (config template)
""",
    )
    parser.add_argument("module", help="Python module name to introspect")
    parser.add_argument(
        "--max-depth", type=int, default=2, help="Max introspection depth (default: 2)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Verify we're in project root
    cwd = Path.cwd()
    skill_dir = cwd / ".claude" / "skills" / "create-introspect-mcp"

    if not skill_dir.exists():
        print("ERROR: Must run from project root directory", file=sys.stderr)
        print(f"Expected to find: {skill_dir}", file=sys.stderr)
        print(f"Current directory: {cwd}", file=sys.stderr)
        sys.exit(1)

    # Setup paths
    introspect_json = cwd / f"{args.module}_introspection.json"
    api_db = cwd / f"{args.module}_api.db"
    server_dir = cwd / f"{args.module}_mcp_server"

    # Detect Python environment
    python_cmd = detect_environment()
    print(f"Detected Python environment: {' '.join(python_cmd)}")
    print(f"Module: {args.module}")
    print(f"Max depth: {args.max_depth}")
    print(f"Output directory: {cwd}")

    # Phase 1: Introspection
    introspect_cmd = python_cmd + [
        str(skill_dir / "scripts" / "introspect.py"),
        args.module,
        "--output",
        str(introspect_json),
        "--max-depth",
        str(args.max_depth),
    ]
    run_phase("1. Module Introspection", introspect_cmd)

    # Phase 2: Database Creation
    db_cmd = python_cmd + [
        str(skill_dir / "scripts" / "create_database.py"),
        str(introspect_json),
        "--output",
        str(api_db),
    ]
    if args.verbose:
        db_cmd.append("--verbose")
    run_phase("2. Database Creation", db_cmd)

    # Phase 3: MCP Server Generation
    server_cmd = python_cmd + [
        str(skill_dir / "scripts" / "create_mcp_server.py"),
        args.module,
        "--database",
        str(api_db),
        "--output",
        str(server_dir),
    ]
    run_phase("3. MCP Server Generation", server_cmd)

    # Phase 4: Create Configuration Templates
    print(f"\n{'=' * 70}")
    print("PHASE: 4. Configuration Template Creation")
    print(f"{'=' * 70}\n")

    mcp_template, settings_template = create_mcp_config_template(args.module, server_dir, api_db)

    print(f"✓ Created: {mcp_template}")
    print(f"✓ Created: {settings_template}")

    # Success!
    print("\n" + "=" * 70)
    print("SUCCESS! MCP Server Created")
    print("=" * 70)
    print(f"\nServer location: {server_dir}")
    print(f"Database: {api_db} ({api_db.stat().st_size / 1024 / 1024:.2f} MB)")
    print("\nConfiguration templates:")
    print(f"  - {mcp_template}")
    print(f"  - {settings_template}")
    print("\nNext steps:")
    print(f"  1. Copy {mcp_template} contents to .mcp.json")
    print(f"  2. Copy {settings_template} contents to .claude/settings.local.json")
    print("  3. Restart Claude Code")
    print(f"  4. Test with: 'Search for {args.module} classes'")
    print()


if __name__ == "__main__":
    main()
