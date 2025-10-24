"""Pytest configuration and shared fixtures."""

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_module_data() -> dict[str, Any]:
    """Sample introspection data for testing."""
    return {
        "name": "test_module",
        "docstring": "A test module for validation",
        "classes": [
            {
                "name": "TestClass",
                "qualified_name": "test_module.TestClass",
                "docstring": "A test class",
                "bases": ["object"],
                "module_name": "test_module",
                "methods": [
                    {
                        "name": "test_method",
                        "qualified_name": "test_module.TestClass.test_method",
                        "signature_string": "(self, x: int) -> str",
                        "docstring": "A test method",
                        "parameters": [
                            {"name": "self", "kind": "POSITIONAL_OR_KEYWORD"},
                            {
                                "name": "x",
                                "kind": "POSITIONAL_OR_KEYWORD",
                                "annotation": "int",
                            },
                        ],
                        "return_annotation": "str",
                        "is_async": False,
                        "is_classmethod": False,
                        "is_staticmethod": False,
                        "class_name": "TestClass",
                        "module_name": "test_module",
                    }
                ],
            }
        ],
        "functions": [
            {
                "name": "test_function",
                "qualified_name": "test_module.test_function",
                "signature_string": "(a: str, b: int = 5) -> bool",
                "docstring": "A test function",
                "parameters": [
                    {"name": "a", "kind": "POSITIONAL_OR_KEYWORD", "annotation": "str"},
                    {
                        "name": "b",
                        "kind": "POSITIONAL_OR_KEYWORD",
                        "annotation": "int",
                        "default": "5",
                    },
                ],
                "return_annotation": "bool",
                "is_async": False,
                "is_classmethod": False,
                "is_staticmethod": False,
                "module_name": "test_module",
            }
        ],
        "submodules": [],
    }


@pytest.fixture
def sample_json_file(temp_dir, sample_module_data):
    """Create a sample JSON file with introspection data."""
    json_path = temp_dir / "sample_data.json"
    with open(json_path, "w") as f:
        json.dump(sample_module_data, f, indent=2)
    return json_path


@pytest.fixture
def sample_database(temp_dir, sample_json_file):
    """Create a sample SQLite database."""
    db_path = temp_dir / "test.db"

    # Import and use create_database functionality
    from src.scripts.create_database import DatabaseCreator

    creator = DatabaseCreator(str(db_path), verbose=False)

    # Load JSON data
    with open(sample_json_file) as f:
        data = json.load(f)

    creator.create(data)

    return db_path


@pytest.fixture
def sample_server_dir(temp_dir, sample_database):
    """Create a sample MCP server directory."""
    server_dir = temp_dir / "mcp_server"
    server_dir.mkdir()

    # Import and use create_mcp_server functionality
    from src.scripts.create_mcp_server import create_mcp_server

    create_mcp_server("test_module", str(sample_database), str(server_dir))

    return server_dir
