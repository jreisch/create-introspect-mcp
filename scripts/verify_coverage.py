#!/usr/bin/env python3
"""
Verify example coverage in the database.

Usage:
    python verify_coverage.py DATABASE_PATH

Example:
    python verify_coverage.py requests_api.db
"""

import argparse
import sqlite3
import sys
from pathlib import Path


def verify_coverage(db_path: str) -> dict:
    """Check coverage statistics for examples"""
    conn = sqlite3.connect(db_path)

    # Get counts
    stats = {}

    cursor = conn.execute("SELECT COUNT(*) FROM examples")
    stats["total_examples"] = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM functions")
    stats["total_functions"] = cursor.fetchone()[0]

    cursor = conn.execute("SELECT COUNT(*) FROM classes")
    stats["total_classes"] = cursor.fetchone()[0]

    cursor = conn.execute("""
        SELECT COUNT(DISTINCT function_id)
        FROM examples
        WHERE function_id IS NOT NULL
    """)
    stats["functions_covered"] = cursor.fetchone()[0]

    cursor = conn.execute("""
        SELECT COUNT(DISTINCT class_id)
        FROM examples
        WHERE class_id IS NOT NULL
    """)
    stats["classes_covered"] = cursor.fetchone()[0]

    # Check for orphaned examples
    cursor = conn.execute("""
        SELECT COUNT(*) FROM examples
        WHERE function_id IS NULL AND class_id IS NULL
    """)
    stats["orphaned_examples"] = cursor.fetchone()[0]

    # Get average examples per entity
    if stats["functions_covered"] > 0:
        cursor = conn.execute("""
            SELECT AVG(example_count) FROM (
                SELECT COUNT(*) as example_count
                FROM examples
                WHERE function_id IS NOT NULL
                GROUP BY function_id
            )
        """)
        stats["avg_examples_per_function"] = cursor.fetchone()[0]
    else:
        stats["avg_examples_per_function"] = 0

    if stats["classes_covered"] > 0:
        cursor = conn.execute("""
            SELECT AVG(example_count) FROM (
                SELECT COUNT(*) as example_count
                FROM examples
                WHERE class_id IS NOT NULL
                GROUP BY class_id
            )
        """)
        stats["avg_examples_per_class"] = cursor.fetchone()[0]
    else:
        stats["avg_examples_per_class"] = 0

    conn.close()

    return stats


def print_report(stats: dict):
    """Print coverage report"""
    print("=" * 70)
    print("Example Coverage Report")
    print("=" * 70)
    print(f"\nTotal Examples: {stats['total_examples']}")

    if stats['total_functions'] > 0:
        func_pct = 100 * stats['functions_covered'] / stats['total_functions']
        print(f"\nFunction Coverage: {stats['functions_covered']}/{stats['total_functions']} "
              f"({func_pct:.1f}%)")
        if stats['functions_covered'] > 0:
            print(f"  Avg examples per function: {stats['avg_examples_per_function']:.2f}")

    if stats['total_classes'] > 0:
        class_pct = 100 * stats['classes_covered'] / stats['total_classes']
        print(f"\nClass Coverage: {stats['classes_covered']}/{stats['total_classes']} "
              f"({class_pct:.1f}%)")
        if stats['classes_covered'] > 0:
            print(f"  Avg examples per class: {stats['avg_examples_per_class']:.2f}")

    if stats['orphaned_examples'] > 0:
        print(f"\n⚠️  Warning: {stats['orphaned_examples']} orphaned examples "
              f"(not linked to any function or class)")
    else:
        print("\n✓ No orphaned examples")

    # Overall status
    print("\n" + "=" * 70)
    if stats['total_functions'] > 0 and stats['total_classes'] > 0:
        total_entities = stats['total_functions'] + stats['total_classes']
        covered_entities = stats['functions_covered'] + stats['classes_covered']
        overall_pct = 100 * covered_entities / total_entities
        print(f"Overall Coverage: {covered_entities}/{total_entities} entities ({overall_pct:.1f}%)")

        if overall_pct == 100:
            print("✓ 100% API COVERAGE ACHIEVED!")
        elif overall_pct >= 80:
            print("✓ Good coverage")
        elif overall_pct >= 50:
            print("⚠ Moderate coverage - consider adding more examples")
        else:
            print("✗ Low coverage - many entities need examples")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Verify example coverage in database")
    parser.add_argument("database", help="Path to the SQLite database")

    args = parser.parse_args()

    db_path = Path(args.database)
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return 1

    stats = verify_coverage(str(db_path))
    print_report(stats)

    return 0


if __name__ == "__main__":
    sys.exit(main())
