"""
Tests for verify_coverage.py
"""

import sqlite3
import sys
from pathlib import Path

import pytest

# Import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "scripts"))
from verify_coverage import print_report, verify_coverage


class TestVerifyCoverage:
    """Test coverage verification logic"""

    def create_test_database(self, db_path: Path):
        """Helper to create a test database with schema"""
        conn = sqlite3.connect(str(db_path))

        # Create schema
        conn.execute("""
            CREATE TABLE functions (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE classes (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE examples (
                id INTEGER PRIMARY KEY,
                code TEXT,
                description TEXT,
                function_id INTEGER,
                class_id INTEGER,
                FOREIGN KEY (function_id) REFERENCES functions(id),
                FOREIGN KEY (class_id) REFERENCES classes(id)
            )
        """)

        conn.commit()
        return conn

    def test_verify_empty_database(self, tmp_path):
        """Test verification of empty database"""
        db_path = tmp_path / "test.db"
        conn = self.create_test_database(db_path)
        conn.close()

        stats = verify_coverage(str(db_path))

        assert stats["total_examples"] == 0
        assert stats["total_functions"] == 0
        assert stats["total_classes"] == 0
        assert stats["functions_covered"] == 0
        assert stats["classes_covered"] == 0
        assert stats["orphaned_examples"] == 0

    def test_verify_with_functions_only(self, tmp_path):
        """Test verification with functions but no examples"""
        db_path = tmp_path / "test.db"
        conn = self.create_test_database(db_path)

        # Add functions
        for i in range(10):
            conn.execute("INSERT INTO functions (name) VALUES (?)", (f"func{i}",))

        conn.commit()
        conn.close()

        stats = verify_coverage(str(db_path))

        assert stats["total_functions"] == 10
        assert stats["functions_covered"] == 0
        assert stats["total_examples"] == 0

    def test_verify_with_complete_function_coverage(self, tmp_path):
        """Test verification with 100% function coverage"""
        db_path = tmp_path / "test.db"
        conn = self.create_test_database(db_path)

        # Add functions
        for i in range(10):
            conn.execute("INSERT INTO functions (name) VALUES (?)", (f"func{i}",))

        # Add examples for each function
        for func_id in range(1, 11):
            for example_num in range(3):
                conn.execute(
                    "INSERT INTO examples (code, description, function_id, class_id) VALUES (?, ?, ?, ?)",
                    (f"code{example_num}", f"desc{example_num}", func_id, None),
                )

        conn.commit()
        conn.close()

        stats = verify_coverage(str(db_path))

        assert stats["total_functions"] == 10
        assert stats["functions_covered"] == 10
        assert stats["total_examples"] == 30
        assert stats["avg_examples_per_function"] == 3.0
        assert stats["orphaned_examples"] == 0

    def test_verify_with_partial_coverage(self, tmp_path):
        """Test verification with partial coverage"""
        db_path = tmp_path / "test.db"
        conn = self.create_test_database(db_path)

        # Add 10 functions
        for i in range(10):
            conn.execute("INSERT INTO functions (name) VALUES (?)", (f"func{i}",))

        # Add examples for only first 5 functions
        for func_id in range(1, 6):
            conn.execute(
                "INSERT INTO examples (code, description, function_id, class_id) VALUES (?, ?, ?, ?)",
                ("code", "desc", func_id, None),
            )

        conn.commit()
        conn.close()

        stats = verify_coverage(str(db_path))

        assert stats["total_functions"] == 10
        assert stats["functions_covered"] == 5
        assert stats["total_examples"] == 5

    def test_verify_with_class_coverage(self, tmp_path):
        """Test verification with class examples"""
        db_path = tmp_path / "test.db"
        conn = self.create_test_database(db_path)

        # Add classes
        for i in range(5):
            conn.execute("INSERT INTO classes (name) VALUES (?)", (f"Class{i}",))

        # Add examples for each class
        for class_id in range(1, 6):
            for example_num in range(2):
                conn.execute(
                    "INSERT INTO examples (code, description, function_id, class_id) VALUES (?, ?, ?, ?)",
                    (f"code{example_num}", f"desc{example_num}", None, class_id),
                )

        conn.commit()
        conn.close()

        stats = verify_coverage(str(db_path))

        assert stats["total_classes"] == 5
        assert stats["classes_covered"] == 5
        assert stats["total_examples"] == 10
        assert stats["avg_examples_per_class"] == 2.0
        assert stats["orphaned_examples"] == 0

    def test_verify_with_orphaned_examples(self, tmp_path):
        """Test detection of orphaned examples"""
        db_path = tmp_path / "test.db"
        conn = self.create_test_database(db_path)

        # Add orphaned examples (both function_id and class_id are NULL)
        for i in range(3):
            conn.execute(
                "INSERT INTO examples (code, description, function_id, class_id) VALUES (?, ?, ?, ?)",
                (f"orphan{i}", "orphaned example", None, None),
            )

        conn.commit()
        conn.close()

        stats = verify_coverage(str(db_path))

        assert stats["total_examples"] == 3
        assert stats["orphaned_examples"] == 3

    def test_verify_realistic_scenario(self, tmp_path):
        """Test with realistic scenario similar to igraph"""
        db_path = tmp_path / "test.db"
        conn = self.create_test_database(db_path)

        # Simulate igraph stats: 177 functions, 44 classes
        for i in range(177):
            conn.execute("INSERT INTO functions (name) VALUES (?)", (f"func{i}",))

        for i in range(44):
            conn.execute("INSERT INTO classes (name) VALUES (?)", (f"Class{i}",))

        # Add ~500 function examples (average 2.8 per function)
        for func_id in range(1, 178):
            num_examples = 3 if func_id <= 60 else 2
            for _ in range(num_examples):
                conn.execute(
                    "INSERT INTO examples (code, description, function_id, class_id) VALUES (?, ?, ?, ?)",
                    ("code", "desc", func_id, None),
                )

        # Add ~150 class examples (average 3.4 per class)
        for class_id in range(1, 45):
            for _ in range(3):
                conn.execute(
                    "INSERT INTO examples (code, description, function_id, class_id) VALUES (?, ?, ?, ?)",
                    ("code", "desc", None, class_id),
                )

        conn.commit()
        conn.close()

        stats = verify_coverage(str(db_path))

        assert stats["total_functions"] == 177
        assert stats["total_classes"] == 44
        assert stats["functions_covered"] == 177
        assert stats["classes_covered"] == 44
        assert 2.0 <= stats["avg_examples_per_function"] <= 3.5
        assert stats["avg_examples_per_class"] == 3.0


class TestPrintReport:
    """Test report printing (smoke tests)"""

    def test_print_report_with_complete_coverage(self, capsys):
        """Test report with 100% coverage"""
        stats = {
            "total_examples": 100,
            "total_functions": 50,
            "total_classes": 20,
            "functions_covered": 50,
            "classes_covered": 20,
            "orphaned_examples": 0,
            "avg_examples_per_function": 1.5,
            "avg_examples_per_class": 1.0,
        }

        print_report(stats)
        captured = capsys.readouterr()

        assert "100%" in captured.out or "100.0%" in captured.out
        assert "✓" in captured.out
        assert "70 entities" in captured.out or "100.0%" in captured.out

    def test_print_report_with_partial_coverage(self, capsys):
        """Test report with partial coverage"""
        stats = {
            "total_examples": 50,
            "total_functions": 100,
            "total_classes": 20,
            "functions_covered": 50,
            "classes_covered": 10,
            "orphaned_examples": 0,
            "avg_examples_per_function": 1.0,
            "avg_examples_per_class": 2.5,
        }

        print_report(stats)
        captured = capsys.readouterr()

        assert "50.0%" in captured.out or "50%" in captured.out

    def test_print_report_with_orphaned_examples(self, capsys):
        """Test report with orphaned examples warning"""
        stats = {
            "total_examples": 60,
            "total_functions": 50,
            "total_classes": 0,
            "functions_covered": 50,
            "classes_covered": 0,
            "orphaned_examples": 10,
            "avg_examples_per_function": 1.0,
            "avg_examples_per_class": 0,
        }

        print_report(stats)
        captured = capsys.readouterr()

        assert "orphaned" in captured.out.lower() or "⚠" in captured.out

    def test_print_report_with_no_classes(self, capsys):
        """Test report when database has no classes"""
        stats = {
            "total_examples": 100,
            "total_functions": 100,
            "total_classes": 0,
            "functions_covered": 100,
            "classes_covered": 0,
            "orphaned_examples": 0,
            "avg_examples_per_function": 1.0,
            "avg_examples_per_class": 0,
        }

        print_report(stats)
        captured = capsys.readouterr()

        # Should handle gracefully without division by zero
        assert "Function Coverage" in captured.out


class TestIntegration:
    """Integration tests"""

    @pytest.mark.integration
    def test_full_verification_workflow(self, tmp_path):
        """Test complete verification workflow"""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))

        # Create realistic database
        conn.execute("""
            CREATE TABLE functions (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE classes (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE examples (
                id INTEGER PRIMARY KEY,
                code TEXT,
                description TEXT,
                function_id INTEGER,
                class_id INTEGER
            )
        """)

        # Add data
        for i in range(20):
            conn.execute("INSERT INTO functions (name) VALUES (?)", (f"func{i}",))
            conn.execute(
                "INSERT INTO examples (code, function_id) VALUES (?, ?)",
                (f"code{i}", i + 1),
            )

        for i in range(10):
            conn.execute("INSERT INTO classes (name) VALUES (?)", (f"Class{i}",))
            conn.execute(
                "INSERT INTO examples (code, class_id) VALUES (?, ?)",
                (f"code{i}", i + 1),
            )

        conn.commit()
        conn.close()

        # Run verification
        stats = verify_coverage(str(db_path))

        # Verify results
        assert stats["total_functions"] == 20
        assert stats["total_classes"] == 10
        assert stats["functions_covered"] == 20
        assert stats["classes_covered"] == 10
        assert stats["total_examples"] == 30
        assert stats["orphaned_examples"] == 0
