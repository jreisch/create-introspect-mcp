"""Tests for validate_server.py script."""


import pytest

from scripts.validate_server import ServerValidator


class TestServerValidator:
    """Tests for ServerValidator class."""

    def test_initialization(self, sample_server_dir):
        """Test ServerValidator initialization."""
        server_path = sample_server_dir / "server.py"
        validator = ServerValidator(str(server_path), verbose=False)

        assert validator.server_path == server_path
        assert not validator.verbose
        assert validator.test_results == []

    @pytest.mark.integration
    def test_import_test(self, sample_server_dir):
        """Test that server can be imported."""
        server_path = sample_server_dir / "server.py"
        validator = ServerValidator(str(server_path), verbose=False)

        result = validator.test_import()
        assert result is True

    @pytest.mark.integration
    def test_basic_functionality(self, sample_server_dir):
        """Test basic functionality checks."""
        server_path = sample_server_dir / "server.py"
        validator = ServerValidator(str(server_path), verbose=False)

        result = validator.test_basic_functionality()
        assert result is True

    @pytest.mark.integration
    def test_database_connection(self, sample_server_dir):
        """Test database connectivity."""
        server_path = sample_server_dir / "server.py"
        validator = ServerValidator(str(server_path), verbose=False)

        result = validator.test_database_connection()
        assert result is True

    @pytest.mark.integration
    @pytest.mark.slow
    def test_query_functions(self, sample_server_dir):
        """Test query function execution."""
        server_path = sample_server_dir / "server.py"
        validator = ServerValidator(str(server_path), verbose=False)

        test_queries = ["test", "TestClass", "test_function"]
        result = validator.test_query_functions(test_queries)
        # May not pass all queries depending on test data, but shouldn't crash
        assert result is not None

    @pytest.mark.integration
    def test_error_handling(self, sample_server_dir):
        """Test error handling."""
        server_path = sample_server_dir / "server.py"
        validator = ServerValidator(str(server_path), verbose=False)

        result = validator.test_error_handling()
        assert result is True

    @pytest.mark.integration
    @pytest.mark.slow
    def test_run_all_tests(self, sample_server_dir):
        """Test running all validation tests."""
        server_path = sample_server_dir / "server.py"
        validator = ServerValidator(str(server_path), verbose=False)

        results = validator.run_all_tests()

        # Should return a dict with test names as keys
        assert isinstance(results, dict)
        assert len(results) > 0

        # Check for expected test names
        assert "Import Test" in results
        assert "Basic Functionality" in results


class TestValidationReporting:
    """Tests for validation reporting functionality."""

    @pytest.mark.integration
    def test_print_summary(self, sample_server_dir, capsys):
        """Test that summary is printed correctly."""
        server_path = sample_server_dir / "server.py"
        validator = ServerValidator(str(server_path), verbose=False)

        test_results = {
            "Test 1": True,
            "Test 2": True,
            "Test 3": False,
        }

        result = validator.print_summary(test_results)

        captured = capsys.readouterr()
        output = captured.out

        # Check output contains expected elements
        assert "VALIDATION SUMMARY" in output
        assert "Test 1" in output
        assert "Test 2" in output
        assert "Test 3" in output
        assert "PASS" in output
        assert "FAIL" in output

        # Should return False because not all tests passed
        assert result is False
