#!/usr/bin/env python3
"""
Environment-aware script runner for introspection scripts.

Detects the project's dependency manager (uv, poetry, pip) and runs
the script with the appropriate command.

Usage:
    python run_with_env.py <script_path> [args...]
    python run_with_env.py scripts/introspect.py requests --output requests.json
"""

import subprocess
import sys
from pathlib import Path


def detect_environment():
    """Detect which dependency manager is being used"""
    cwd = Path.cwd()

    # Check for uv
    if (cwd / "uv.lock").exists():
        return "uv"

    # Check for pyproject.toml with uv configuration
    pyproject = cwd / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            if "[tool.uv]" in content or "uv" in content.lower():
                return "uv"
        except Exception:
            pass

    # Check for poetry
    if (cwd / "poetry.lock").exists():
        return "poetry"

    # Check for pipenv
    if (cwd / "Pipfile").exists():
        return "pipenv"

    # Check for conda
    if (cwd / "environment.yml").exists() or (cwd / "environment.yaml").exists():
        return "conda"

    # Default to system python
    return "python"


def run_script(script_path: str, args: list[str]):
    """Run script with appropriate environment manager"""
    env_type = detect_environment()

    if env_type == "uv":
        # Use --no-project to avoid build issues with pyproject.toml
        cmd = ["uv", "run", "--no-project", "python", script_path] + args
    elif env_type == "poetry":
        cmd = ["poetry", "run", "python", script_path] + args
    elif env_type == "pipenv":
        cmd = ["pipenv", "run", "python", script_path] + args
    elif env_type == "conda":
        cmd = ["conda", "run", "python", script_path] + args
    else:
        cmd = ["python", script_path] + args

    print(f"[run_with_env] Detected environment: {env_type}", file=sys.stderr)
    print(f"[run_with_env] Running: {' '.join(cmd)}", file=sys.stderr)
    print("", file=sys.stderr)

    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: run_with_env.py <script_path> [args...]", file=sys.stderr)
        print("", file=sys.stderr)
        print("Example:", file=sys.stderr)
        print(
            "  python run_with_env.py scripts/introspect.py requests --output requests.json",
            file=sys.stderr,
        )
        sys.exit(1)

    run_script(sys.argv[1], sys.argv[2:])
