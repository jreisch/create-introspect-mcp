"""
Tests for divide_entities.py
"""

import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "scripts"))
from divide_entities import divide_entities, export_entities


class TestExportEntities:
    """Test entity export from database"""

    def test_export_entities_empty_database(self, tmp_path):
        """Test exporting from empty database"""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))

        # Create schema
        conn.execute("""
            CREATE TABLE classes (
                id INTEGER PRIMARY KEY,
                name TEXT,
                full_qualified_name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE functions (
                id INTEGER PRIMARY KEY,
                name TEXT,
                full_qualified_name TEXT
            )
        """)
        conn.commit()
        conn.close()

        entities = export_entities(str(db_path))
        assert entities == []

    def test_export_entities_with_data(self, tmp_path):
        """Test exporting entities with data"""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))

        # Create schema
        conn.execute("""
            CREATE TABLE classes (
                id INTEGER PRIMARY KEY,
                name TEXT,
                full_qualified_name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE functions (
                id INTEGER PRIMARY KEY,
                name TEXT,
                full_qualified_name TEXT
            )
        """)

        # Insert test data
        conn.execute(
            "INSERT INTO classes (name, full_qualified_name) VALUES (?, ?)",
            ("TestClass", "module.TestClass"),
        )
        conn.execute(
            "INSERT INTO functions (name, full_qualified_name) VALUES (?, ?)",
            ("test_func", "module.test_func"),
        )
        conn.commit()
        conn.close()

        entities = export_entities(str(db_path))

        assert len(entities) == 2
        assert any(e["type"] == "CLASS" and e["name"] == "TestClass" for e in entities)
        assert any(e["type"] == "FUNCTION" and e["name"] == "test_func" for e in entities)

    def test_export_entities_with_multiple_items(self, tmp_path):
        """Test exporting multiple classes and functions"""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))

        # Create schema
        conn.execute("""
            CREATE TABLE classes (
                id INTEGER PRIMARY KEY,
                name TEXT,
                full_qualified_name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE functions (
                id INTEGER PRIMARY KEY,
                name TEXT,
                full_qualified_name TEXT
            )
        """)

        # Insert multiple items
        for i in range(5):
            conn.execute(
                "INSERT INTO classes (name, full_qualified_name) VALUES (?, ?)",
                (f"Class{i}", f"module.Class{i}"),
            )
            conn.execute(
                "INSERT INTO functions (name, full_qualified_name) VALUES (?, ?)",
                (f"func{i}", f"module.func{i}"),
            )

        conn.commit()
        conn.close()

        entities = export_entities(str(db_path))

        assert len(entities) == 10
        # Check all have required fields
        for entity in entities:
            assert "type" in entity
            assert "id" in entity
            assert "name" in entity
            assert "full_qualified_name" in entity
            assert entity["type"] in ["CLASS", "FUNCTION"]


class TestDivideEntities:
    """Test entity division logic"""

    def test_divide_empty_list(self):
        """Test dividing empty list"""
        entities = []
        groups = divide_entities(entities, num_groups=10)

        assert len(groups) == 10
        assert all(len(g) == 0 for g in groups)

    def test_divide_single_entity(self):
        """Test dividing single entity"""
        entities = [{"id": 1, "name": "test"}]
        groups = divide_entities(entities, num_groups=10)

        assert len(groups) == 10
        # One group should have the entity
        assert sum(len(g) for g in groups) == 1

    def test_divide_even_distribution(self):
        """Test even distribution of entities"""
        entities = [{"id": i, "name": f"entity{i}"} for i in range(100)]
        groups = divide_entities(entities, num_groups=10)

        assert len(groups) == 10
        # Each group should have exactly 10 entities
        assert all(len(g) == 10 for g in groups)

    def test_divide_uneven_distribution(self):
        """Test distribution with remainder"""
        entities = [{"id": i, "name": f"entity{i}"} for i in range(95)]
        groups = divide_entities(entities, num_groups=10)

        assert len(groups) == 10
        # Total should still be 95
        assert sum(len(g) for g in groups) == 95

        # First 5 groups should have 10, remaining should have 9
        sizes = [len(g) for g in groups]
        assert sizes.count(10) == 5
        assert sizes.count(9) == 5

    def test_divide_fewer_entities_than_groups(self):
        """Test when there are fewer entities than groups"""
        entities = [{"id": i, "name": f"entity{i}"} for i in range(5)]
        groups = divide_entities(entities, num_groups=10)

        assert len(groups) == 10
        # Total should still be 5
        assert sum(len(g) for g in groups) == 5

        # 5 groups should have 1, others should have 0
        sizes = [len(g) for g in groups]
        assert sizes.count(1) == 5
        assert sizes.count(0) == 5

    def test_divide_reproducibility(self):
        """Test that division is reproducible with same seed"""
        entities = [{"id": i, "name": f"entity{i}"} for i in range(50)]

        groups1 = divide_entities(entities, num_groups=10)
        groups2 = divide_entities(entities, num_groups=10)

        # Should produce identical groupings
        for g1, g2 in zip(groups1, groups2, strict=True):
            assert g1 == g2

    def test_divide_single_group(self):
        """Test division into a single group"""
        entities = [{"id": i, "name": f"entity{i}"} for i in range(20)]
        groups = divide_entities(entities, num_groups=1)

        assert len(groups) == 1
        assert len(groups[0]) == 20


class TestMain:
    """Tests for main() function"""

    @patch("sys.argv", ["divide_entities.py", "test.db"])
    def test_main_success(self, tmp_path, monkeypatch):
        """Test successful main() execution"""
        from divide_entities import main

        monkeypatch.chdir(tmp_path)

        # Create test database
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE classes (
                id INTEGER PRIMARY KEY,
                name TEXT,
                full_qualified_name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE functions (
                id INTEGER PRIMARY KEY,
                name TEXT,
                full_qualified_name TEXT
            )
        """)
        for i in range(10):
            conn.execute(
                "INSERT INTO classes (name, full_qualified_name) VALUES (?, ?)",
                (f"Class{i}", f"module.Class{i}"),
            )
        conn.commit()
        conn.close()

        # Run main
        result = main()

        assert result == 0
        # Verify files were created in /tmp
        assert Path("/tmp/entity_group_1.json").exists()

    @patch("sys.argv", ["divide_entities.py", "nonexistent.db"])
    def test_main_database_not_found(self):
        """Test main() with nonexistent database"""
        from divide_entities import main

        result = main()

        assert result == 1

    @patch("sys.argv", ["divide_entities.py", "test.db", "--groups", "5"])
    def test_main_with_groups_argument(self, tmp_path, monkeypatch):
        """Test main() with custom number of groups"""
        from divide_entities import main

        monkeypatch.chdir(tmp_path)

        # Create test database
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE classes (
                id INTEGER PRIMARY KEY,
                name TEXT,
                full_qualified_name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE functions (
                id INTEGER PRIMARY KEY,
                name TEXT,
                full_qualified_name TEXT
            )
        """)
        for i in range(15):
            conn.execute(
                "INSERT INTO functions (name, full_qualified_name) VALUES (?, ?)",
                (f"func{i}", f"module.func{i}"),
            )
        conn.commit()
        conn.close()

        # Run main with 5 groups
        result = main()

        assert result == 0
        # Verify 5 group files were created
        for i in range(1, 6):
            assert Path(f"/tmp/entity_group_{i}.json").exists()

    @patch("sys.argv", ["divide_entities.py", "test.db", "--output-dir", "custom_output"])
    def test_main_with_custom_output_dir(self, tmp_path, monkeypatch):
        """Test main() with custom output directory"""
        from divide_entities import main

        monkeypatch.chdir(tmp_path)

        # Create test database
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE classes (
                id INTEGER PRIMARY KEY,
                name TEXT,
                full_qualified_name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE functions (
                id INTEGER PRIMARY KEY,
                name TEXT,
                full_qualified_name TEXT
            )
        """)
        for i in range(20):
            conn.execute(
                "INSERT INTO classes (name, full_qualified_name) VALUES (?, ?)",
                (f"Class{i}", f"module.Class{i}"),
            )
        conn.commit()
        conn.close()

        # Create custom output directory
        output_dir = tmp_path / "custom_output"

        # Run main
        result = main()

        assert result == 0
        # Verify files in custom directory
        assert output_dir.exists()
        assert (output_dir / "entity_group_1.json").exists()

    @patch("sys.argv", ["divide_entities.py", "test.db", "--groups", "3", "--output-dir", "out"])
    def test_main_with_all_arguments(self, tmp_path, monkeypatch, capsys):
        """Test main() with all arguments"""
        from divide_entities import main

        monkeypatch.chdir(tmp_path)

        # Create test database
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE classes (
                id INTEGER PRIMARY KEY,
                name TEXT,
                full_qualified_name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE functions (
                id INTEGER PRIMARY KEY,
                name TEXT,
                full_qualified_name TEXT
            )
        """)
        for i in range(30):
            conn.execute(
                "INSERT INTO functions (name, full_qualified_name) VALUES (?, ?)",
                (f"func{i}", f"module.func{i}"),
            )
        conn.commit()
        conn.close()

        # Create output directory
        output_dir = tmp_path / "out"

        # Run main
        result = main()

        assert result == 0

        # Verify output messages
        captured = capsys.readouterr()
        assert "Found 30 entities" in captured.out
        assert "Dividing into 3 groups" in captured.out
        assert "Total entities: 30" in captured.out

        # Verify files
        for i in range(1, 4):
            filepath = output_dir / f"entity_group_{i}.json"
            assert filepath.exists()


class TestIntegration:
    """Integration tests for divide_entities script"""

    @pytest.mark.integration
    def test_full_workflow(self, tmp_path):
        """Test complete export and divide workflow"""
        # Create database with realistic data
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))

        conn.execute("""
            CREATE TABLE classes (
                id INTEGER PRIMARY KEY,
                name TEXT,
                full_qualified_name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE functions (
                id INTEGER PRIMARY KEY,
                name TEXT,
                full_qualified_name TEXT
            )
        """)

        # Insert realistic data
        for i in range(44):
            conn.execute(
                "INSERT INTO classes (name, full_qualified_name) VALUES (?, ?)",
                (f"Class{i}", f"module.Class{i}"),
            )

        for i in range(177):
            conn.execute(
                "INSERT INTO functions (name, full_qualified_name) VALUES (?, ?)",
                (f"function{i}", f"module.function{i}"),
            )

        conn.commit()
        conn.close()

        # Export entities
        entities = export_entities(str(db_path))
        assert len(entities) == 221  # 44 classes + 177 functions

        # Divide into groups
        groups = divide_entities(entities, num_groups=10)
        assert len(groups) == 10

        # Verify total count preserved
        assert sum(len(g) for g in groups) == 221

        # Verify each group has reasonable size (20-23 entities)
        for group in groups:
            assert 20 <= len(group) <= 23

    @pytest.mark.integration
    def test_write_group_files(self, tmp_path):
        """Test writing group files to disk"""
        entities = [{"id": i, "name": f"entity{i}", "type": "CLASS"} for i in range(30)]
        groups = divide_entities(entities, num_groups=3)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Write groups to files
        for i, group in enumerate(groups, 1):
            filename = output_dir / f"entity_group_{i}.json"
            with open(filename, "w") as f:
                json.dump(group, f, indent=2)

        # Verify files were created
        for i in range(1, 4):
            filename = output_dir / f"entity_group_{i}.json"
            assert filename.exists()

            # Verify content
            with open(filename) as f:
                data = json.load(f)
                assert isinstance(data, list)
                assert len(data) == 10  # 30 entities / 3 groups
