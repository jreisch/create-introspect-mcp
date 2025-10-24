"""Tests for create_database.py script."""

import sqlite3

import pytest

from src.scripts.create_database import DatabaseCreator


class TestDatabaseCreator:
    """Tests for DatabaseCreator class."""

    def test_initialization(self, temp_dir):
        """Test DatabaseCreator initialization."""
        db_path = temp_dir / "test.db"
        creator = DatabaseCreator(str(db_path), verbose=False)

        assert creator.db_path == str(db_path)
        assert not creator.verbose
        assert creator.module_ids == {}
        assert creator.class_ids == {}

    def test_create_schema(self, temp_dir):
        """Test database schema creation."""
        db_path = temp_dir / "test.db"
        creator = DatabaseCreator(str(db_path), verbose=False)
        creator.conn = sqlite3.connect(str(db_path))
        creator.conn.execute("PRAGMA foreign_keys = ON")

        creator.create_schema()

        # Verify tables exist
        cursor = creator.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        expected_tables = {
            "modules",
            "classes",
            "class_inheritance",
            "functions",
            "parameters",
            "examples",
            "classes_fts",
            "functions_fts",
        }

        assert expected_tables.issubset(tables)
        creator.conn.close()

    def test_insert_module(self, temp_dir):
        """Test inserting a module."""
        db_path = temp_dir / "test.db"
        creator = DatabaseCreator(str(db_path), verbose=False)
        creator.conn = sqlite3.connect(str(db_path))
        creator.conn.execute("PRAGMA foreign_keys = ON")
        creator.create_schema()

        module_data = {"name": "test_module", "docstring": "Test module"}

        module_id = creator.insert_module(module_data)

        assert module_id > 0
        assert "test_module" in creator.module_ids
        assert creator.module_ids["test_module"] == module_id

        # Verify in database
        cursor = creator.conn.execute(
            "SELECT name, docstring FROM modules WHERE id = ?", (module_id,)
        )
        row = cursor.fetchone()
        assert row[0] == "test_module"
        assert row[1] == "Test module"

        creator.conn.close()

    def test_insert_class(self, temp_dir):
        """Test inserting a class."""
        db_path = temp_dir / "test.db"
        creator = DatabaseCreator(str(db_path), verbose=False)
        creator.conn = sqlite3.connect(str(db_path))
        creator.conn.execute("PRAGMA foreign_keys = ON")
        creator.create_schema()

        # Insert module first
        module_data = {"name": "test_module", "docstring": None}
        module_id = creator.insert_module(module_data)

        # Insert class
        class_data = {
            "name": "TestClass",
            "qualified_name": "test_module.TestClass",
            "docstring": "A test class",
            "bases": ["object"],
            "methods": [],
        }

        creator.insert_class(class_data, module_id)

        # Verify in database
        cursor = creator.conn.execute("SELECT name FROM classes WHERE module_id = ?", (module_id,))
        row = cursor.fetchone()
        assert row[0] == "TestClass"

        creator.conn.close()

    def test_insert_function(self, temp_dir):
        """Test inserting a function."""
        db_path = temp_dir / "test.db"
        creator = DatabaseCreator(str(db_path), verbose=False)
        creator.conn = sqlite3.connect(str(db_path))
        creator.conn.execute("PRAGMA foreign_keys = ON")
        creator.create_schema()

        # Insert module
        module_data = {"name": "test_module", "docstring": None}
        module_id = creator.insert_module(module_data)

        # Insert function
        func_data = {
            "name": "test_func",
            "qualified_name": "test_module.test_func",
            "signature_string": "(x: int) -> str",
            "docstring": "Test function",
            "parameters": [{"name": "x", "kind": "POSITIONAL_OR_KEYWORD", "annotation": "int"}],
            "return_annotation": "str",
            "is_async": False,
            "is_classmethod": False,
            "is_staticmethod": False,
        }

        creator.insert_function(func_data, module_id, None)

        # Verify in database
        cursor = creator.conn.execute(
            "SELECT name FROM functions WHERE module_id = ?", (module_id,)
        )
        row = cursor.fetchone()
        assert row[0] == "test_func"

        # Verify parameters
        cursor = creator.conn.execute("SELECT COUNT(*) FROM parameters")
        count = cursor.fetchone()[0]
        assert count == 1

        creator.conn.close()

    @pytest.mark.integration
    def test_full_database_creation(self, temp_dir, sample_module_data):
        """Test complete database creation workflow."""
        db_path = temp_dir / "test.db"
        creator = DatabaseCreator(str(db_path), verbose=False)

        creator.create(sample_module_data)

        # Verify database exists
        assert db_path.exists()

        # Check contents
        conn = sqlite3.connect(str(db_path))

        cursor = conn.execute("SELECT COUNT(*) FROM modules")
        assert cursor.fetchone()[0] > 0

        cursor = conn.execute("SELECT COUNT(*) FROM classes")
        assert cursor.fetchone()[0] > 0

        cursor = conn.execute("SELECT COUNT(*) FROM functions")
        assert cursor.fetchone()[0] > 0

        cursor = conn.execute("SELECT COUNT(*) FROM parameters")
        assert cursor.fetchone()[0] > 0

        conn.close()

    @pytest.mark.integration
    def test_fts_search_works(self, temp_dir, sample_module_data):
        """Test that FTS5 search works after database creation."""
        db_path = temp_dir / "test.db"
        creator = DatabaseCreator(str(db_path), verbose=False)
        creator.create(sample_module_data)

        conn = sqlite3.connect(str(db_path))

        # Search for "test" in classes
        cursor = conn.execute(
            """
            SELECT c.name
            FROM classes_fts
            JOIN classes c ON classes_fts.rowid = c.id
            WHERE classes_fts MATCH 'test'
        """
        )
        results = cursor.fetchall()
        assert len(results) > 0

        conn.close()


class TestDatabaseStatistics:
    """Tests for database statistics functionality."""

    def test_get_stats(self, sample_database):
        """Test getting database statistics."""
        conn = sqlite3.connect(str(sample_database))

        cursor = conn.execute("SELECT COUNT(*) FROM classes")
        class_count = cursor.fetchone()[0]
        assert class_count > 0

        cursor = conn.execute("SELECT COUNT(*) FROM functions")
        function_count = cursor.fetchone()[0]
        assert function_count > 0

        conn.close()


class TestRootModuleFeature:
    """Tests for root_module support."""

    def test_get_root_module_simple(self):
        """Test extracting root module from simple module name."""
        assert DatabaseCreator.get_root_module("requests") == "requests"

    def test_get_root_module_submodule(self):
        """Test extracting root module from submodule."""
        assert DatabaseCreator.get_root_module("requests.models") == "requests"

    def test_get_root_module_nested(self):
        """Test extracting root module from deeply nested module."""
        assert DatabaseCreator.get_root_module("requests.models.auth.basic") == "requests"

    def test_get_root_module_no_dot(self):
        """Test module name without dots returns itself."""
        assert DatabaseCreator.get_root_module("numpy") == "numpy"

    def test_root_module_stored_in_database(self, temp_dir):
        """Test that root_module is stored in database."""
        db_path = temp_dir / "test.db"
        creator = DatabaseCreator(str(db_path), verbose=False)
        creator.conn = sqlite3.connect(str(db_path))
        creator.conn.execute("PRAGMA foreign_keys = ON")
        creator.create_schema()

        # Insert module with submodule name
        module_data = {"name": "requests.models", "docstring": "Models submodule"}

        module_id = creator.insert_module(module_data)

        # Verify root_module is stored correctly
        cursor = creator.conn.execute(
            "SELECT name, root_module FROM modules WHERE id = ?", (module_id,)
        )
        row = cursor.fetchone()
        assert row[0] == "requests.models"
        assert row[1] == "requests"

        creator.conn.close()

    def test_root_module_index_exists(self, temp_dir):
        """Test that index on root_module column exists."""
        db_path = temp_dir / "test.db"
        creator = DatabaseCreator(str(db_path), verbose=False)
        creator.conn = sqlite3.connect(str(db_path))
        creator.conn.execute("PRAGMA foreign_keys = ON")
        creator.create_schema()

        # Check that index exists
        cursor = creator.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_modules_root'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "idx_modules_root"

        creator.conn.close()

    def test_multiple_modules_same_root(self, temp_dir):
        """Test inserting multiple modules with same root."""
        db_path = temp_dir / "test.db"
        creator = DatabaseCreator(str(db_path), verbose=False)
        creator.conn = sqlite3.connect(str(db_path))
        creator.conn.execute("PRAGMA foreign_keys = ON")
        creator.create_schema()

        # Insert multiple submodules
        modules = [
            {"name": "requests.models", "docstring": "Models"},
            {"name": "requests.auth", "docstring": "Auth"},
            {"name": "requests.sessions", "docstring": "Sessions"},
        ]

        for module_data in modules:
            creator.insert_module(module_data)

        # Verify all have same root_module
        cursor = creator.conn.execute("SELECT DISTINCT root_module FROM modules")
        roots = cursor.fetchall()
        assert len(roots) == 1
        assert roots[0][0] == "requests"

        # Verify count
        cursor = creator.conn.execute("SELECT COUNT(*) FROM modules WHERE root_module = 'requests'")
        count = cursor.fetchone()[0]
        assert count == 3

        creator.conn.close()

    def test_query_by_root_module(self, temp_dir):
        """Test querying modules by root_module."""
        db_path = temp_dir / "test.db"
        creator = DatabaseCreator(str(db_path), verbose=False)
        creator.conn = sqlite3.connect(str(db_path))
        creator.conn.execute("PRAGMA foreign_keys = ON")
        creator.create_schema()

        # Insert modules from different roots
        modules = [
            {"name": "requests.models", "docstring": "Requests models"},
            {"name": "requests.auth", "docstring": "Requests auth"},
            {"name": "httpx.models", "docstring": "HTTPX models"},
            {"name": "urllib3.connection", "docstring": "urllib3 connection"},
        ]

        for module_data in modules:
            creator.insert_module(module_data)

        # Query for requests modules only
        cursor = creator.conn.execute(
            "SELECT name FROM modules WHERE root_module = 'requests' ORDER BY name"
        )
        results = cursor.fetchall()
        assert len(results) == 2
        assert results[0][0] == "requests.auth"
        assert results[1][0] == "requests.models"

        creator.conn.close()
