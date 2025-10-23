#!/usr/bin/env python3
"""
SQLite Database Creation Tool for Python Module Introspection Data

Takes JSON output from introspect.py and creates a normalized SQLite database
with FTS5 full-text search capabilities.

Features:
- Normalized schema with foreign keys
- FTS5 full-text search tables
- Proper indexes for performance
- Statistics and validation

Usage:
    python create_database.py data.json --output module_api.db
    python create_database.py data.json --output module_api.db --verbose
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


class DatabaseCreator:
    """Creates SQLite database from introspection JSON"""

    def __init__(self, db_path: str, verbose: bool = False):
        self.db_path = db_path
        self.verbose = verbose
        self.conn: sqlite3.Connection | None = None

        # Track IDs for foreign keys
        self.module_ids: dict[str, int] = {}
        self.class_ids: dict[str, int] = {}

    def log(self, message: str):
        """Log message if verbose mode enabled"""
        if self.verbose:
            print(message, file=sys.stderr)

    def create_schema(self):
        """Create database schema with FTS5 tables"""
        self.log("Creating database schema...")

        assert self.conn is not None
        cursor = self.conn.cursor()

        # Modules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                docstring TEXT
            )
        """)

        # Classes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                full_qualified_name TEXT NOT NULL UNIQUE,
                docstring TEXT,
                module_id INTEGER NOT NULL,
                FOREIGN KEY (module_id) REFERENCES modules(id)
            )
        """)

        # Inheritance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS class_inheritance (
                class_id INTEGER NOT NULL,
                base_class_name TEXT NOT NULL,
                FOREIGN KEY (class_id) REFERENCES classes(id),
                PRIMARY KEY (class_id, base_class_name)
            )
        """)

        # Functions table (includes both module-level functions and methods)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS functions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                full_qualified_name TEXT NOT NULL UNIQUE,
                signature_string TEXT NOT NULL,
                docstring TEXT,
                return_annotation TEXT,
                is_async INTEGER DEFAULT 0,
                is_classmethod INTEGER DEFAULT 0,
                is_staticmethod INTEGER DEFAULT 0,
                class_id INTEGER,
                module_id INTEGER NOT NULL,
                FOREIGN KEY (class_id) REFERENCES classes(id),
                FOREIGN KEY (module_id) REFERENCES modules(id)
            )
        """)

        # Parameters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parameters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                function_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                annotation TEXT,
                default_value TEXT,
                position INTEGER NOT NULL,
                FOREIGN KEY (function_id) REFERENCES functions(id)
            )
        """)

        # Examples table (for future use if code examples are available)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS examples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                description TEXT,
                function_id INTEGER,
                class_id INTEGER,
                FOREIGN KEY (function_id) REFERENCES functions(id),
                FOREIGN KEY (class_id) REFERENCES classes(id)
            )
        """)

        # Create indexes
        self.log("Creating indexes...")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_classes_module ON classes(module_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_classes_name ON classes(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_functions_class ON functions(class_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_functions_module ON functions(module_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_functions_name ON functions(name)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_parameters_function ON parameters(function_id)"
        )

        # Create FTS5 virtual tables for full-text search
        self.log("Creating FTS5 search tables...")

        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS classes_fts USING fts5(
                name,
                full_qualified_name,
                docstring,
                content='classes',
                content_rowid='id'
            )
        """)

        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS functions_fts USING fts5(
                name,
                full_qualified_name,
                docstring,
                signature_string,
                content='functions',
                content_rowid='id'
            )
        """)

        # Create triggers to keep FTS5 tables in sync
        self.log("Creating FTS5 sync triggers...")

        # Classes FTS triggers
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS classes_ai AFTER INSERT ON classes BEGIN
                INSERT INTO classes_fts(rowid, name, full_qualified_name, docstring)
                VALUES (new.id, new.name, new.full_qualified_name, new.docstring);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS classes_ad AFTER DELETE ON classes BEGIN
                INSERT INTO classes_fts(classes_fts, rowid, name, full_qualified_name, docstring)
                VALUES('delete', old.id, old.name, old.full_qualified_name, old.docstring);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS classes_au AFTER UPDATE ON classes BEGIN
                INSERT INTO classes_fts(classes_fts, rowid, name, full_qualified_name, docstring)
                VALUES('delete', old.id, old.name, old.full_qualified_name, old.docstring);
                INSERT INTO classes_fts(rowid, name, full_qualified_name, docstring)
                VALUES (new.id, new.name, new.full_qualified_name, new.docstring);
            END
        """)

        # Functions FTS triggers
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS functions_ai AFTER INSERT ON functions BEGIN
                INSERT INTO functions_fts(rowid, name, full_qualified_name, docstring, signature_string)
                VALUES (new.id, new.name, new.full_qualified_name, new.docstring, new.signature_string);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS functions_ad AFTER DELETE ON functions BEGIN
                INSERT INTO functions_fts(functions_fts, rowid, name, full_qualified_name, docstring, signature_string)
                VALUES('delete', old.id, old.name, old.full_qualified_name, old.docstring, old.signature_string);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS functions_au AFTER UPDATE ON functions BEGIN
                INSERT INTO functions_fts(functions_fts, rowid, name, full_qualified_name, docstring, signature_string)
                VALUES('delete', old.id, old.name, old.full_qualified_name, old.docstring, old.signature_string);
                INSERT INTO functions_fts(rowid, name, full_qualified_name, docstring, signature_string)
                VALUES (new.id, new.name, new.full_qualified_name, new.docstring, new.signature_string);
            END
        """)

        assert self.conn is not None
        self.conn.commit()

    def insert_module(self, module_data: dict[str, Any]) -> int:
        """Insert a module and return its ID"""
        assert self.conn is not None
        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO modules (name, docstring)
            VALUES (?, ?)
        """,
            (module_data["name"], module_data.get("docstring")),
        )

        module_id = cursor.lastrowid
        assert module_id is not None
        self.module_ids[module_data["name"]] = module_id

        self.log(f"  Inserted module: {module_data['name']} (ID: {module_id})")

        return module_id

    def insert_class(self, class_data: dict[str, Any], module_id: int):
        """Insert a class and its methods"""
        assert self.conn is not None
        cursor = self.conn.cursor()

        # Insert class
        cursor.execute(
            """
            INSERT INTO classes (name, full_qualified_name, docstring, module_id)
            VALUES (?, ?, ?, ?)
        """,
            (
                class_data["name"],
                class_data["qualified_name"],
                class_data.get("docstring"),
                module_id,
            ),
        )

        class_id = cursor.lastrowid
        assert class_id is not None
        self.class_ids[class_data["qualified_name"]] = class_id

        self.log(f"    Inserted class: {class_data['name']} (ID: {class_id})")

        # Insert inheritance
        for base in class_data.get("bases", []):
            cursor.execute(
                """
                INSERT INTO class_inheritance (class_id, base_class_name)
                VALUES (?, ?)
            """,
                (class_id, base),
            )

        # Insert methods
        for method_data in class_data.get("methods", []):
            self.insert_function(method_data, module_id, class_id)

    def insert_function(
        self, func_data: dict[str, Any], module_id: int, class_id: int | None = None
    ):
        """Insert a function and its parameters"""
        assert self.conn is not None
        cursor = self.conn.cursor()

        # Insert function
        cursor.execute(
            """
            INSERT INTO functions (
                name, full_qualified_name, signature_string, docstring,
                return_annotation, is_async, is_classmethod, is_staticmethod,
                class_id, module_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                func_data["name"],
                func_data["qualified_name"],
                func_data["signature_string"],
                func_data.get("docstring"),
                func_data.get("return_annotation"),
                1 if func_data.get("is_async") else 0,
                1 if func_data.get("is_classmethod") else 0,
                1 if func_data.get("is_staticmethod") else 0,
                class_id,
                module_id,
            ),
        )

        function_id = cursor.lastrowid

        func_type = "method" if class_id else "function"
        self.log(f"      Inserted {func_type}: {func_data['name']} (ID: {function_id})")

        # Insert parameters
        for position, param_data in enumerate(func_data.get("parameters", [])):
            cursor.execute(
                """
                INSERT INTO parameters (
                    function_id, name, kind, annotation, default_value, position
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    function_id,
                    param_data["name"],
                    param_data["kind"],
                    param_data.get("annotation"),
                    param_data.get("default"),
                    position,
                ),
            )

    def populate_database(self, data: dict[str, Any]):
        """Populate database from introspection data"""
        self.log("Populating database...")
        assert self.conn is not None

        def process_module(module_data: dict[str, Any]):
            # Insert module
            module_id = self.insert_module(module_data)

            # Insert classes
            for class_data in module_data.get("classes", []):
                self.insert_class(class_data, module_id)

            # Insert module-level functions
            for func_data in module_data.get("functions", []):
                self.insert_function(func_data, module_id)

            # Process submodules recursively
            for submodule_data in module_data.get("submodules", []):
                process_module(submodule_data)

        process_module(data)
        self.conn.commit()

    def print_statistics(self):
        """Print database statistics"""
        assert self.conn is not None
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM modules")
        modules_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM classes")
        classes_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM functions WHERE class_id IS NULL")
        functions_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM functions WHERE class_id IS NOT NULL")
        methods_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM parameters")
        parameters_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM examples")
        examples_count = cursor.fetchone()[0]

        # Get database file size
        db_size = Path(self.db_path).stat().st_size / (1024 * 1024)  # MB

        print("\n" + "=" * 50)
        print("DATABASE STATISTICS")
        print("=" * 50)
        print(f"Database file: {self.db_path}")
        print(f"Database size: {db_size:.2f} MB")
        print(f"\nModules:    {modules_count:,}")
        print(f"Classes:    {classes_count:,}")
        print(f"Functions:  {functions_count:,}")
        print(f"Methods:    {methods_count:,}")
        print(f"Parameters: {parameters_count:,}")
        print(f"Examples:   {examples_count:,}")
        print(f"\nTotal functions: {functions_count + methods_count:,}")
        print("=" * 50)

    def create(self, json_data: dict[str, Any]):
        """Create database from JSON data"""
        # Remove existing database
        db_path = Path(self.db_path)
        if db_path.exists():
            self.log(f"Removing existing database: {db_path}")
            db_path.unlink()

        # Create database connection
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")

        try:
            # Create schema
            self.create_schema()

            # Populate data
            self.populate_database(json_data)

            # Print statistics
            self.print_statistics()

        finally:
            self.conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Create SQLite database from introspection JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="Input JSON file from introspect.py")
    parser.add_argument("--output", "-o", required=True, help="Output SQLite database file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Read JSON data
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading JSON data from: {input_path}", file=sys.stderr)
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    # Create database
    creator = DatabaseCreator(args.output, verbose=args.verbose)
    creator.create(data)

    print(f"\nDatabase created successfully: {args.output}")


if __name__ == "__main__":
    main()
