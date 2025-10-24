#!/usr/bin/env python3
"""
Divide entities into N equal groups for parallel example generation processing.

Usage:
    python divide_entities.py DATABASE_PATH [--groups N]

Example:
    python divide_entities.py requests_api.db --groups 10
"""

import argparse
import json
import random
import sqlite3
import sys
from pathlib import Path


def export_entities(db_path: str) -> list[dict]:
    """Export all entities (classes and functions) from database"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute("""
        SELECT 'CLASS' as type, id, name, full_qualified_name FROM classes
        UNION ALL
        SELECT 'FUNCTION' as type, id, name, full_qualified_name FROM functions
        ORDER BY type, name
    """)

    entities = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return entities


def divide_entities(entities: list[dict], num_groups: int = 10) -> list[list[dict]]:
    """Divide entities into equal groups with shuffling for even distribution"""
    # Shuffle to distribute different types evenly
    shuffled = entities.copy()
    random.seed(42)  # For reproducibility
    random.shuffle(shuffled)

    # Calculate group sizes
    total = len(shuffled)
    base_size = total // num_groups
    remainder = total % num_groups

    groups = []
    start_idx = 0

    for i in range(num_groups):
        # Add 1 extra entity to first 'remainder' groups
        group_size = base_size + (1 if i < remainder else 0)
        end_idx = start_idx + group_size

        group = shuffled[start_idx:end_idx]
        groups.append(group)

        start_idx = end_idx

    return groups


def main():
    parser = argparse.ArgumentParser(description="Divide entities into groups for parallel processing")
    parser.add_argument("database", help="Path to the SQLite database")
    parser.add_argument("--groups", type=int, default=10, help="Number of groups to create (default: 10)")
    parser.add_argument("--output-dir", default="/tmp", help="Output directory for group files (default: /tmp)")

    args = parser.parse_args()

    db_path = Path(args.database)
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    print(f"Exporting entities from {db_path}...")
    entities = export_entities(str(db_path))
    print(f"Found {len(entities)} entities")

    print(f"\nDividing into {args.groups} groups...")
    groups = divide_entities(entities, args.groups)

    # Write each group to a separate file
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, group in enumerate(groups, 1):
        filename = output_dir / f"entity_group_{i}.json"
        with open(filename, "w") as f:
            json.dump(group, f, indent=2)
        print(f"Group {i}: {len(group)} entities -> {filename}")

    print(f"\nTotal entities: {sum(len(g) for g in groups)}")
    print(f"\nGroup files created in: {output_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
