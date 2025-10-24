"""
Tests for run_with_env.py
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "scripts"))
from run_with_env import detect_environment, run_script


class TestDetectEnvironment:
    """Test environment detection"""

    def test_detect_uv_with_lock(self, tmp_path, monkeypatch):
        """Test detection of uv via uv.lock"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "uv.lock").touch()

        result = detect_environment()
        assert result == "uv"

    def test_detect_uv_from_pyproject(self, tmp_path, monkeypatch):
        """Test detection of uv via pyproject.toml"""
        monkeypatch.chdir(tmp_path)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.uv]\ndev-dependencies = []")

        result = detect_environment()
        assert result == "uv"

    def test_detect_poetry(self, tmp_path, monkeypatch):
        """Test detection of poetry"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "poetry.lock").touch()

        result = detect_environment()
        assert result == "poetry"

    def test_detect_pipenv(self, tmp_path, monkeypatch):
        """Test detection of pipenv"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "Pipfile").touch()

        result = detect_environment()
        assert result == "pipenv"

    def test_detect_conda_yml(self, tmp_path, monkeypatch):
        """Test detection of conda via environment.yml"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "environment.yml").touch()

        result = detect_environment()
        assert result == "conda"

    def test_detect_conda_yaml(self, tmp_path, monkeypatch):
        """Test detection of conda via environment.yaml"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "environment.yaml").touch()

        result = detect_environment()
        assert result == "conda"

    def test_detect_system_python(self, tmp_path, monkeypatch):
        """Test fallback to system python"""
        monkeypatch.chdir(tmp_path)

        result = detect_environment()
        assert result == "python"

    def test_priority_uv_over_poetry(self, tmp_path, monkeypatch):
        """Test that uv takes priority when both exist"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "uv.lock").touch()
        (tmp_path / "poetry.lock").touch()

        result = detect_environment()
        assert result == "uv"

    def test_priority_poetry_over_pipenv(self, tmp_path, monkeypatch):
        """Test that poetry takes priority over pipenv"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "poetry.lock").touch()
        (tmp_path / "Pipfile").touch()

        result = detect_environment()
        assert result == "poetry"


class TestRunScript:
    """Test script execution"""

    @patch("subprocess.run")
    @patch("sys.exit")
    def test_run_script_with_uv(self, mock_exit, mock_run, tmp_path, monkeypatch):
        """Test running script with uv"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "uv.lock").touch()

        mock_run.return_value = MagicMock(returncode=0)

        run_script("test.py", ["--arg", "value"])

        # Verify subprocess.run was called with correct command
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd == ["uv", "run", "--no-project", "python", "test.py", "--arg", "value"]
        mock_exit.assert_called_once_with(0)

    @patch("subprocess.run")
    @patch("sys.exit")
    def test_run_script_with_poetry(self, mock_exit, mock_run, tmp_path, monkeypatch):
        """Test running script with poetry"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "poetry.lock").touch()

        mock_run.return_value = MagicMock(returncode=0)

        run_script("test.py", [])

        cmd = mock_run.call_args[0][0]
        assert cmd == ["poetry", "run", "python", "test.py"]
        mock_exit.assert_called_once_with(0)

    @patch("subprocess.run")
    @patch("sys.exit")
    def test_run_script_with_pipenv(self, mock_exit, mock_run, tmp_path, monkeypatch):
        """Test running script with pipenv"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "Pipfile").touch()

        mock_run.return_value = MagicMock(returncode=0)

        run_script("test.py", [])

        cmd = mock_run.call_args[0][0]
        assert cmd == ["pipenv", "run", "python", "test.py"]

    @patch("subprocess.run")
    @patch("sys.exit")
    def test_run_script_with_conda(self, mock_exit, mock_run, tmp_path, monkeypatch):
        """Test running script with conda"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "environment.yml").touch()

        mock_run.return_value = MagicMock(returncode=0)

        run_script("test.py", [])

        cmd = mock_run.call_args[0][0]
        assert cmd == ["conda", "run", "python", "test.py"]

    @patch("subprocess.run")
    @patch("sys.exit")
    def test_run_script_with_system_python(self, mock_exit, mock_run, tmp_path, monkeypatch):
        """Test running script with system python"""
        monkeypatch.chdir(tmp_path)

        mock_run.return_value = MagicMock(returncode=0)

        run_script("test.py", ["arg1", "arg2"])

        cmd = mock_run.call_args[0][0]
        assert cmd == ["python", "test.py", "arg1", "arg2"]

    @patch("subprocess.run")
    @patch("sys.exit")
    def test_run_script_with_failure(self, mock_exit, mock_run, tmp_path, monkeypatch):
        """Test handling of script failure"""
        monkeypatch.chdir(tmp_path)

        mock_run.return_value = MagicMock(returncode=1)

        run_script("test.py", [])

        mock_exit.assert_called_once_with(1)

    @patch("subprocess.run")
    @patch("sys.exit")
    def test_run_script_with_multiple_args(self, mock_exit, mock_run, tmp_path, monkeypatch):
        """Test running script with multiple arguments"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "uv.lock").touch()

        mock_run.return_value = MagicMock(returncode=0)

        args = ["--output", "result.json", "--verbose", "--max-depth", "3"]
        run_script("introspect.py", args)

        cmd = mock_run.call_args[0][0]
        assert cmd[-5:] == args  # Last 5 elements should be our args


class TestIntegration:
    """Integration tests"""

    @pytest.mark.integration
    @patch("subprocess.run")
    @patch("sys.exit")
    def test_realistic_introspection_command(self, mock_exit, mock_run, tmp_path, monkeypatch):
        """Test realistic introspection command"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "uv.lock").touch()

        mock_run.return_value = MagicMock(returncode=0)

        script_path = "scripts/introspect.py"
        args = ["requests", "--output", "requests_data.json"]

        run_script(script_path, args)

        cmd = mock_run.call_args[0][0]
        assert "uv" in cmd
        assert "python" in cmd
        assert script_path in cmd
        assert "requests" in cmd
        assert "requests_data.json" in cmd
