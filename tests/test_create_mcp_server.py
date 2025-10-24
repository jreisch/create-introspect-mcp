"""Tests for create_mcp_server.py script."""

import pytest

from src.scripts.create_mcp_server import create_mcp_server, get_database_stats


class TestGetDatabaseStats:
    """Tests for get_database_stats function."""

    def test_get_stats(self, sample_database):
        """Test getting statistics from database."""
        stats = get_database_stats(str(sample_database))

        assert "class_count" in stats
        assert "function_count" in stats
        assert "method_count" in stats
        assert "parameter_count" in stats
        assert "total_functions" in stats
        assert "db_size_mb" in stats
        assert "tool_count" in stats

        assert stats["class_count"] > 0
        assert stats["tool_count"] == 8
        assert stats["db_size_mb"] > 0


class TestCreateMCPServer:
    """Tests for create_mcp_server function."""

    @pytest.mark.integration
    def test_create_server_files(self, temp_dir, sample_database):
        """Test that all server files are created."""
        output_dir = temp_dir / "mcp_server"
        output_dir.mkdir()

        create_mcp_server("test_module", str(sample_database), str(output_dir))

        # Check that files were created
        assert (output_dir / "server.py").exists()
        assert (output_dir / "pyproject.toml").exists()
        assert (output_dir / "README.md").exists()

    @pytest.mark.integration
    def test_server_py_is_executable(self, temp_dir, sample_database):
        """Test that server.py has executable permissions."""
        output_dir = temp_dir / "mcp_server"
        output_dir.mkdir()

        create_mcp_server("test_module", str(sample_database), str(output_dir))

        server_file = output_dir / "server.py"
        assert server_file.exists()
        # Check executable bit
        assert server_file.stat().st_mode & 0o111  # Any execute bit set

    @pytest.mark.integration
    def test_server_py_has_required_functions(self, temp_dir, sample_database):
        """Test that generated server.py has required functions."""
        output_dir = temp_dir / "mcp_server"
        output_dir.mkdir()

        create_mcp_server("test_module", str(sample_database), str(output_dir))

        server_content = (output_dir / "server.py").read_text()

        # Check for required functions
        assert "def search_api" in server_content
        assert "def get_class_info" in server_content
        assert "def get_function_info" in server_content
        assert "def list_classes" in server_content
        assert "def list_functions" in server_content
        assert "def get_parameters" in server_content
        assert "def find_examples" in server_content
        assert "def get_related" in server_content

    @pytest.mark.integration
    def test_readme_contains_stats(self, temp_dir, sample_database):
        """Test that README contains database statistics."""
        output_dir = temp_dir / "mcp_server"
        output_dir.mkdir()

        create_mcp_server("test_module", str(sample_database), str(output_dir))

        readme_content = (output_dir / "README.md").read_text()

        # Check for stats in README (with markdown bold formatting)
        assert "**Classes**:" in readme_content
        assert "**Functions**:" in readme_content
        assert "**Methods**:" in readme_content

    @pytest.mark.integration
    def test_pyproject_toml_valid(self, temp_dir, sample_database):
        """Test that pyproject.toml is valid TOML."""
        output_dir = temp_dir / "mcp_server"
        output_dir.mkdir()

        create_mcp_server("test_module", str(sample_database), str(output_dir))

        pyproject_file = output_dir / "pyproject.toml"
        content = pyproject_file.read_text()

        # Basic check that it looks like valid TOML
        assert "[project]" in content
        assert 'name = "test_module-introspection"' in content
        assert "dependencies" in content
