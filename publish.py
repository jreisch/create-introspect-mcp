#!/usr/bin/env python3
"""
Publish Script for create-introspect-mcp Claude Code Skill

Creates a clean distribution build containing only the files needed for the
Claude Code skill to function (excludes tests, dev config, etc.).

Usage:
    python publish.py
    python publish.py --build-number 5
    python publish.py --dry-run
"""

import argparse
import shutil
import sys
from pathlib import Path


class SkillPublisher:
    """Publishes Claude Code skill to dist/ directory"""

    def __init__(self, root_dir: Path, dry_run: bool = False):
        self.root_dir = root_dir
        self.dry_run = dry_run
        self.dist_dir = root_dir / "dist"

        # Files/directories to include in the skill distribution
        self.include_patterns = [
            "SKILL.md",  # Main skill definition
            "scripts/introspect.py",
            "scripts/create_database.py",
            "scripts/create_mcp_server.py",
            "scripts/validate_server.py",
            "scripts/requirements.txt",
            "scripts/__init__.py",
        ]

    def get_next_build_number(self) -> int:
        """Find the next build number by scanning existing builds"""
        if not self.dist_dir.exists():
            return 1

        existing_builds = [
            d.name for d in self.dist_dir.iterdir() if d.is_dir() and d.name.startswith("build_")
        ]

        if not existing_builds:
            return 1

        # Extract build numbers
        build_numbers = []
        for build_name in existing_builds:
            try:
                # build_0001 -> 0001 -> 1
                num = int(build_name.split("_")[1])
                build_numbers.append(num)
            except (IndexError, ValueError):
                continue

        return max(build_numbers) + 1 if build_numbers else 1

    def format_build_name(self, build_number: int) -> str:
        """Format build number with padding (e.g., build_0001)"""
        return f"build_{build_number:04d}"

    def create_build_directory(self, build_name: str) -> Path:
        """Create the build directory structure"""
        build_path = self.dist_dir / build_name / "create-introspect-mcp"

        if self.dry_run:
            print(f"[DRY RUN] Would create: {build_path}")
            return build_path

        build_path.mkdir(parents=True, exist_ok=False)
        print(f"✅ Created build directory: {build_path}")
        return build_path

    def copy_skill_files(self, dest_dir: Path):
        """Copy all skill files to the build directory"""
        print("\n📦 Copying skill files...")

        copied_count = 0
        for pattern in self.include_patterns:
            source_path = self.root_dir / pattern
            dest_path = dest_dir / pattern

            if not source_path.exists():
                print(f"⚠️  Warning: Source file not found: {pattern}")
                continue

            # Create parent directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            if self.dry_run:
                print(f"[DRY RUN] Would copy: {pattern}")
            else:
                shutil.copy2(source_path, dest_path)
                print(f"  ✓ {pattern}")

            copied_count += 1

        return copied_count

    def create_build_info(self, dest_dir: Path, build_name: str):
        """Create a BUILD_INFO.txt file with metadata"""
        from datetime import datetime

        info_path = dest_dir / "BUILD_INFO.txt"
        build_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        content = f"""Create-Introspect-MCP Claude Code Skill
Build: {build_name}
Date: {build_time}

This is a clean distribution containing only the files needed for the
Claude Code skill to function.

To use this skill:
1. Copy this entire directory to your project's .claude/skills/ directory
2. Restart Claude Code
3. The skill will be available when you ask Claude to create MCP servers

Files included:
"""

        for pattern in self.include_patterns:
            content += f"  - {pattern}\n"

        if self.dry_run:
            print(f"\n[DRY RUN] Would create BUILD_INFO.txt")
        else:
            info_path.write_text(content)
            print(f"\n✅ Created BUILD_INFO.txt")

    def publish(self, build_number: int | None = None) -> Path | None:
        """Execute the publish workflow"""
        print("🚀 Publishing create-introspect-mcp skill...\n")

        # Determine build number
        if build_number is None:
            build_number = self.get_next_build_number()
        build_name = self.format_build_name(build_number)

        print(f"Build number: {build_number} ({build_name})")

        # Create build directory
        try:
            build_dir = self.create_build_directory(build_name)
        except FileExistsError:
            print(f"\n❌ Error: Build {build_name} already exists!")
            print("   Use --build-number to specify a different build number")
            return None

        # Copy skill files
        copied_count = self.copy_skill_files(build_dir)

        if copied_count == 0:
            print("\n❌ Error: No files were copied!")
            return None

        # Create build info
        self.create_build_info(build_dir, build_name)

        # Success summary
        print(f"\n{'=' * 60}")
        print(f"✅ Build {build_name} complete!")
        print(f"{'=' * 60}")
        print(f"\nLocation: {build_dir}")
        print(f"Files copied: {copied_count}")

        if not self.dry_run:
            print(f"\nTo use this build:")
            print(f"  cp -r {build_dir} /path/to/your/project/.claude/skills/")
        else:
            print(f"\n[DRY RUN] No files were actually copied")

        return build_dir


def main():
    parser = argparse.ArgumentParser(
        description="Publish create-introspect-mcp Claude Code skill",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python publish.py                    # Auto-increment build number
  python publish.py --build-number 5   # Use specific build number
  python publish.py --dry-run          # Preview without copying
        """,
    )

    parser.add_argument(
        "--build-number",
        type=int,
        help="Specify build number (default: auto-increment)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be copied without actually copying",
    )

    args = parser.parse_args()

    # Determine root directory (where this script lives)
    root_dir = Path(__file__).parent

    # Create publisher and run
    publisher = SkillPublisher(root_dir, dry_run=args.dry_run)

    try:
        result = publisher.publish(build_number=args.build_number)
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
