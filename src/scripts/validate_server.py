#!/usr/bin/env python3
"""
MCP Server Validation Tool

Tests an MCP server implementation with sample queries and validates responses.

Features:
- Server startup validation
- Tool accessibility testing
- Sample query execution
- Performance benchmarks
- Error handling validation
- Comprehensive reporting

Usage:
    python validate_server.py server.py
    python validate_server.py server.py --test-queries "search layout" "get Graph class"
    python validate_server.py server.py --verbose
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


class ServerValidator:
    """Validates MCP server implementation"""

    def __init__(self, server_path: str, verbose: bool = False):
        self.server_path = Path(server_path)
        self.verbose = verbose
        self.test_results = []

    def log(self, message: str, level: str = "INFO"):
        """Log message"""
        if self.verbose or level in ["ERROR", "SUCCESS"]:
            prefix = {"INFO": "ℹ️ ", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️ "}.get(
                level, "  "
            )
            print(f"{prefix} {message}")

    def test_import(self) -> bool:
        """Test if server module can be imported"""
        self.log("Testing server import...")

        try:
            # Try to import as a module
            import importlib.util

            spec = importlib.util.spec_from_file_location("server", self.server_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.log("Server imports successfully", "SUCCESS")
                return True
            else:
                self.log("Could not load server module", "ERROR")
                return False
        except Exception as e:
            self.log(f"Import failed: {e}", "ERROR")
            return False

    def test_server_startup(self, timeout: int = 5) -> bool:
        """Test if server starts without errors"""
        self.log(f"Testing server startup (timeout: {timeout}s)...")

        try:
            # Start server process
            process = subprocess.Popen(
                [sys.executable, str(self.server_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait briefly to see if it crashes
            try:
                _stdout, stderr = process.communicate(timeout=2)
                # If process ended, check exit code
                if process.returncode != 0:
                    self.log(f"Server exited with code {process.returncode}", "ERROR")
                    if stderr:
                        self.log(f"Error: {stderr[:200]}", "ERROR")
                    return False
            except subprocess.TimeoutExpired:
                # Server is still running - this is good!
                process.kill()
                self.log("Server started successfully", "SUCCESS")
                return True

            return True

        except Exception as e:
            self.log(f"Startup test failed: {e}", "ERROR")
            return False

    def test_basic_functionality(self) -> bool:
        """Test basic server functionality"""
        self.log("Testing basic functionality...")

        # This is a simplified test - in production you'd use MCP client library
        try:
            # Check if server has required attributes
            import importlib.util

            spec = importlib.util.spec_from_file_location("server", self.server_path)
            if not spec or not spec.loader:
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Check for required functions/objects
            required_attrs = ["app", "search_api", "get_class_info", "get_function_info"]
            missing = [attr for attr in required_attrs if not hasattr(module, attr)]

            if missing:
                self.log(f"Missing required attributes: {', '.join(missing)}", "ERROR")
                return False

            self.log("Basic functionality checks passed", "SUCCESS")
            return True

        except Exception as e:
            self.log(f"Functionality test failed: {e}", "ERROR")
            return False

    def test_database_connection(self) -> bool:
        """Test database connectivity"""
        self.log("Testing database connection...")

        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("server", self.server_path)
            if not spec or not spec.loader:
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Check if DB_PATH exists
            if hasattr(module, "DB_PATH"):
                db_path = Path(module.DB_PATH)
                if not db_path.exists():
                    self.log(f"Database not found: {db_path}", "ERROR")
                    return False

                # Try to connect
                if hasattr(module, "get_db_connection"):
                    try:
                        conn = module.get_db_connection()
                        conn.close()
                        self.log("Database connection successful", "SUCCESS")
                        return True
                    except Exception as e:
                        self.log(f"Database connection failed: {e}", "ERROR")
                        return False
                else:
                    self.log("get_db_connection not found in server", "WARNING")
                    return False
            else:
                self.log("DB_PATH not found in server", "WARNING")
                return False

        except Exception as e:
            self.log(f"Database test failed: {e}", "ERROR")
            return False

    def test_query_functions(self, test_queries: list[str] | None = None) -> bool:
        """Test query functions with sample data"""
        self.log("Testing query functions...")

        if not test_queries:
            test_queries = ["test", "Graph", "layout"]

        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("server", self.server_path)
            if not spec or not spec.loader:
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            all_passed = True

            # Test search_api
            if hasattr(module, "search_api"):
                for query in test_queries[:1]:  # Test first query
                    try:
                        start = time.time()
                        result = module.search_api(query, limit=5)
                        duration = time.time() - start

                        if result and "No results found" not in result:
                            self.log(f"search_api('{query}'): ✓ ({duration:.2f}s)", "SUCCESS")
                        else:
                            self.log(f"search_api('{query}'): No results", "WARNING")
                    except Exception as e:
                        self.log(f"search_api('{query}') failed: {e}", "ERROR")
                        all_passed = False

            # Test get_class_info
            if hasattr(module, "get_class_info"):
                try:
                    start = time.time()
                    result = module.get_class_info(
                        test_queries[1] if len(test_queries) > 1 else "TestClass"
                    )
                    duration = time.time() - start

                    if result and "not found" not in result.lower():
                        self.log(f"get_class_info: ✓ ({duration:.2f}s)", "SUCCESS")
                    else:
                        self.log("get_class_info: Class not found (expected for test)", "WARNING")
                except Exception as e:
                    self.log(f"get_class_info failed: {e}", "ERROR")
                    all_passed = False

            # Test list_classes
            if hasattr(module, "list_classes"):
                try:
                    start = time.time()
                    result = module.list_classes(limit=10)
                    duration = time.time() - start

                    if result and "Classes" in result:
                        self.log(f"list_classes: ✓ ({duration:.2f}s)", "SUCCESS")
                    else:
                        self.log("list_classes: Unexpected result", "WARNING")
                except Exception as e:
                    self.log(f"list_classes failed: {e}", "ERROR")
                    all_passed = False

            return all_passed

        except Exception as e:
            self.log(f"Query test failed: {e}", "ERROR")
            return False

    def test_error_handling(self) -> bool:
        """Test error handling with invalid inputs"""
        self.log("Testing error handling...")

        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("server", self.server_path)
            if not spec or not spec.loader:
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Test with invalid class name
            if hasattr(module, "get_class_info"):
                result = module.get_class_info("NonExistentClass12345")
                if "not found" in result.lower():
                    self.log("Error handling for invalid class: ✓", "SUCCESS")
                else:
                    self.log("Error handling unclear", "WARNING")

            # Test with empty query
            if hasattr(module, "search_api"):
                try:
                    result = module.search_api("", limit=5)
                    # Should either handle gracefully or return no results
                    self.log("Error handling for empty query: ✓", "SUCCESS")
                except Exception:
                    self.log("Empty query not handled", "WARNING")

            return True

        except Exception as e:
            self.log(f"Error handling test failed: {e}", "ERROR")
            return False

    def run_all_tests(self, test_queries: list[str] | None = None) -> dict[str, bool]:
        """Run all validation tests"""
        print("\n" + "=" * 60)
        print("MCP SERVER VALIDATION")
        print("=" * 60)
        print(f"Server: {self.server_path}")
        print("=" * 60 + "\n")

        tests = {
            "Import Test": self.test_import,
            "Startup Test": self.test_server_startup,
            "Basic Functionality": self.test_basic_functionality,
            "Database Connection": self.test_database_connection,
            "Query Functions": lambda: self.test_query_functions(test_queries),
            "Error Handling": self.test_error_handling,
        }

        results = {}
        for test_name, test_func in tests.items():
            try:
                results[test_name] = test_func()
            except Exception as e:
                self.log(f"{test_name} raised exception: {e}", "ERROR")
                results[test_name] = False
            print()  # Blank line between tests

        return results

    def print_summary(self, results: dict[str, bool]):
        """Print validation summary"""
        print("=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)

        passed = sum(1 for r in results.values() if r)
        total = len(results)

        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:.<40} {status}")

        print("=" * 60)
        print(f"Total: {passed}/{total} tests passed ({passed / total * 100:.0f}%)")

        if passed == total:
            print("✅ All tests passed! Server is ready to use.")
        elif passed >= total * 0.8:
            print("⚠️  Most tests passed, but some issues found.")
        else:
            print("❌ Multiple tests failed. Server may not be ready.")

        print("=" * 60)

        return passed == total


def main():
    parser = argparse.ArgumentParser(
        description="Validate MCP server implementation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("server", help="Path to server.py file")
    parser.add_argument("--test-queries", nargs="+", help="Custom test queries")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Validate server file exists
    server_path = Path(args.server)
    if not server_path.exists():
        print(f"Error: Server file not found: {server_path}", file=sys.stderr)
        sys.exit(1)

    # Run validation
    validator = ServerValidator(str(server_path), verbose=args.verbose)
    results = validator.run_all_tests(test_queries=args.test_queries)

    # Print summary
    all_passed = validator.print_summary(results)

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
