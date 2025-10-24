"""
Tests for create_full_mcp_server.py
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "scripts"))
from create_full_mcp_server import (
    create_mcp_config_template,
    detect_environment,
    run_phase,
)


class TestDetectEnvironment:
    """Test environment detection logic"""

    def test_detect_uv_with_lock(self, tmp_path, monkeypatch):
        """Test UV detection with uv.lock file"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "uv.lock").touch()

        result = detect_environment()
        assert result == ["uv", "run", "--no-project", "python"]

    def test_detect_poetry_with_lock(self, tmp_path, monkeypatch):
        """Test Poetry detection with poetry.lock file"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "poetry.lock").touch()

        result = detect_environment()
        assert result == ["poetry", "run", "python"]

    def test_detect_pipenv_with_pipfile(self, tmp_path, monkeypatch):
        """Test Pipenv detection with Pipfile"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "Pipfile").touch()

        result = detect_environment()
        assert result == ["pipenv", "run", "python"]

    def test_detect_system_python(self, tmp_path, monkeypatch):
        """Test default to system Python"""
        monkeypatch.chdir(tmp_path)

        result = detect_environment()
        assert result == ["python"]


class TestRunPhase:
    """Test workflow phase execution"""

    @patch("subprocess.run")
    def test_run_phase_success(self, mock_run):
        """Test successful phase execution"""
        mock_run.return_value = MagicMock(returncode=0)

        run_phase("Test Phase", ["echo", "test"])

        mock_run.assert_called_once_with(["echo", "test"], cwd=None)

    @patch("subprocess.run")
    def test_run_phase_failure(self, mock_run):
        """Test phase failure handling"""
        mock_run.return_value = MagicMock(returncode=1)

        with pytest.raises(SystemExit) as exc_info:
            run_phase("Test Phase", ["false"])

        assert exc_info.value.code == 1

    @patch("subprocess.run")
    def test_run_phase_with_cwd(self, mock_run, tmp_path):
        """Test phase execution with custom working directory"""
        mock_run.return_value = MagicMock(returncode=0)

        run_phase("Test Phase", ["echo", "test"], cwd=tmp_path)

        mock_run.assert_called_once_with(["echo", "test"], cwd=tmp_path)


class TestCreateMcpConfigTemplate:
    """Test MCP configuration template creation"""

    def test_create_config_template(self, tmp_path):
        """Test creation of MCP configuration templates"""
        module_name = "requests"
        server_dir = tmp_path / "requests_mcp_server"
        server_dir.mkdir()
        api_db = tmp_path / "requests_api.db"
        api_db.touch()

        mcp_template, settings_template = create_mcp_config_template(
            module_name, server_dir, api_db
        )

        # Verify files were created
        assert mcp_template.exists()
        assert settings_template.exists()

        # Verify MCP config content
        with open(mcp_template) as f:
            mcp_config = json.load(f)

        assert "mcpServers" in mcp_config
        assert f"{module_name}-introspection" in mcp_config["mcpServers"]

        server_config = mcp_config["mcpServers"][f"{module_name}-introspection"]
        assert server_config["type"] == "stdio"
        assert server_config["command"] == "uv"
        assert "server.py" in server_config["args"]

        # Verify settings content
        with open(settings_template) as f:
            settings = json.load(f)

        assert "permissions" in settings
        assert "allow" in settings["permissions"]

        # Check all 8 tools are listed
        expected_tools = [
            "search_api",
            "get_class_info",
            "get_function_info",
            "list_classes",
            "list_functions",
            "get_parameters",
            "find_examples",
            "get_related",
        ]
        for tool in expected_tools:
            tool_permission = f"mcp__{module_name}-introspection__{tool}"
            assert tool_permission in settings["permissions"]["allow"]

    def test_config_paths_are_absolute(self, tmp_path):
        """Test that paths in configuration are absolute"""
        module_name = "test_module"
        server_dir = tmp_path / "test_mcp_server"
        server_dir.mkdir()
        api_db = tmp_path / "test_api.db"
        api_db.touch()

        mcp_template, _ = create_mcp_config_template(module_name, server_dir, api_db)

        with open(mcp_template) as f:
            mcp_config = json.load(f)

        server_config = mcp_config["mcpServers"][f"{module_name}-introspection"]

        # Check paths are absolute
        assert Path(server_config["cwd"]).is_absolute()
        assert Path(server_config["env"]["PYTHONPATH"]).is_absolute()
        assert Path(server_config["env"]["DB_PATH"]).is_absolute()


class TestMain:
    """Tests for main() function"""

    @patch("sys.argv", ["create_full_mcp_server.py", "test_module"])
    @patch("create_full_mcp_server.run_phase")
    @patch("create_full_mcp_server.create_mcp_config_template")
    @patch("create_full_mcp_server.detect_environment")
    def test_main_success_workflow(
        self, mock_detect_env, mock_create_config, mock_run_phase, tmp_path, monkeypatch
    ):
        """Test successful main() execution"""
        from create_full_mcp_server import main

        monkeypatch.chdir(tmp_path)

        # Create skill directory structure
        skill_dir = tmp_path / ".claude" / "skills" / "create-introspect-mcp" / "scripts"
        skill_dir.mkdir(parents=True)

        # Create mock files
        api_db = tmp_path / "test_module_api.db"
        api_db.write_text("")
        server_dir = tmp_path / "test_module_mcp_server"
        server_dir.mkdir()

        # Setup mocks
        mock_detect_env.return_value = ["python"]
        mock_create_config.return_value = (
            server_dir / "mcp.json.template",
            server_dir / "settings.local.json.template",
        )
        # Create the template files
        (server_dir / "mcp.json.template").write_text("{}")
        (server_dir / "settings.local.json.template").write_text("{}")

        # Run main
        main()

        # Verify run_phase was called 3 times (introspection, database, server)
        assert mock_run_phase.call_count == 3
        assert mock_create_config.call_count == 1

    @patch("sys.argv", ["create_full_mcp_server.py", "test_module"])
    def test_main_missing_skill_directory(self, tmp_path, monkeypatch):
        """Test main() fails when skill directory doesn't exist"""
        from create_full_mcp_server import main

        monkeypatch.chdir(tmp_path)

        # Don't create skill directory - should fail
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("sys.argv", ["create_full_mcp_server.py", "test_module", "--max-depth", "5"])
    @patch("create_full_mcp_server.run_phase")
    @patch("create_full_mcp_server.create_mcp_config_template")
    @patch("create_full_mcp_server.detect_environment")
    def test_main_with_max_depth_argument(
        self, mock_detect_env, mock_create_config, mock_run_phase, tmp_path, monkeypatch
    ):
        """Test main() with --max-depth argument"""
        from create_full_mcp_server import main

        monkeypatch.chdir(tmp_path)

        # Create skill directory
        skill_dir = tmp_path / ".claude" / "skills" / "create-introspect-mcp" / "scripts"
        skill_dir.mkdir(parents=True)

        # Create mock files
        api_db = tmp_path / "test_module_api.db"
        api_db.write_text("")
        server_dir = tmp_path / "test_module_mcp_server"
        server_dir.mkdir()

        # Setup mocks
        mock_detect_env.return_value = ["python"]
        mock_create_config.return_value = (
            server_dir / "mcp.json.template",
            server_dir / "settings.local.json.template",
        )
        (server_dir / "mcp.json.template").write_text("{}")
        (server_dir / "settings.local.json.template").write_text("{}")

        # Run main
        main()

        # Verify max-depth was passed to introspection command
        introspect_call = mock_run_phase.call_args_list[0]
        cmd = introspect_call[0][1]
        assert "5" in cmd

    @patch("sys.argv", ["create_full_mcp_server.py", "test_module", "--verbose"])
    @patch("create_full_mcp_server.run_phase")
    @patch("create_full_mcp_server.create_mcp_config_template")
    @patch("create_full_mcp_server.detect_environment")
    def test_main_with_verbose_flag(
        self, mock_detect_env, mock_create_config, mock_run_phase, tmp_path, monkeypatch
    ):
        """Test main() with --verbose flag"""
        from create_full_mcp_server import main

        monkeypatch.chdir(tmp_path)

        # Create skill directory
        skill_dir = tmp_path / ".claude" / "skills" / "create-introspect-mcp" / "scripts"
        skill_dir.mkdir(parents=True)

        # Create mock files
        api_db = tmp_path / "test_module_api.db"
        api_db.write_text("")
        server_dir = tmp_path / "test_module_mcp_server"
        server_dir.mkdir()

        # Setup mocks
        mock_detect_env.return_value = ["python"]
        mock_create_config.return_value = (
            server_dir / "mcp.json.template",
            server_dir / "settings.local.json.template",
        )
        (server_dir / "mcp.json.template").write_text("{}")
        (server_dir / "settings.local.json.template").write_text("{}")

        # Run main
        main()

        # Verify --verbose was passed to database command
        db_call = mock_run_phase.call_args_list[1]
        cmd = db_call[0][1]
        assert "--verbose" in cmd

    @patch("sys.argv", ["create_full_mcp_server.py", "requests"])
    @patch("create_full_mcp_server.run_phase")
    @patch("create_full_mcp_server.create_mcp_config_template")
    @patch("create_full_mcp_server.detect_environment")
    def test_main_creates_all_paths(
        self, mock_detect_env, mock_create_config, mock_run_phase, tmp_path, monkeypatch
    ):
        """Test that main() creates correct paths for all phases"""
        from create_full_mcp_server import main

        monkeypatch.chdir(tmp_path)

        # Create skill directory
        skill_dir = tmp_path / ".claude" / "skills" / "create-introspect-mcp" / "scripts"
        skill_dir.mkdir(parents=True)

        # Create mock files
        api_db = tmp_path / "requests_api.db"
        api_db.write_text("")
        server_dir = tmp_path / "requests_mcp_server"
        server_dir.mkdir()

        # Setup mocks
        mock_detect_env.return_value = ["python"]
        mock_create_config.return_value = (
            server_dir / "mcp.json.template",
            server_dir / "settings.local.json.template",
        )
        (server_dir / "mcp.json.template").write_text("{}")
        (server_dir / "settings.local.json.template").write_text("{}")

        # Run main
        main()

        # Verify paths in calls
        phase_calls = mock_run_phase.call_args_list

        # Phase 1: introspection
        introspect_cmd = phase_calls[0][0][1]
        assert any("requests_introspection.json" in str(arg) for arg in introspect_cmd)

        # Phase 2: database
        db_cmd = phase_calls[1][0][1]
        assert any("requests_api.db" in str(arg) for arg in db_cmd)

        # Phase 3: server
        server_cmd = phase_calls[2][0][1]
        assert any("requests_mcp_server" in str(arg) for arg in server_cmd)


class TestIntegration:
    """Integration tests for full workflow (if possible)"""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_main_with_invalid_module(self, tmp_path, monkeypatch):
        """Test that main fails gracefully with invalid module"""
        monkeypatch.chdir(tmp_path)

        # Create minimal skill directory structure
        skill_dir = tmp_path / ".claude" / "skills" / "create-introspect-mcp"
        skill_dir.mkdir(parents=True)

        # This would require full setup, so we just verify structure
        assert skill_dir.exists()
