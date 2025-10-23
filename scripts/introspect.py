#!/usr/bin/env python3
"""
Python Module Introspection Tool

Introspects a Python module to extract classes, functions, methods, parameters,
docstrings, and type information. Outputs structured JSON for database creation.

Features:
- Extracts classes with inheritance information
- Captures functions and methods with full signatures
- Preserves docstrings and type hints
- Handles parameters with defaults and annotations
- Gracefully handles C extensions (may have limited introspection)
- Recursive module exploration

Usage:
    python introspect.py MODULE_NAME --output data.json
    python introspect.py MODULE_NAME --output data.json --max-depth 2
    python introspect.py MODULE_NAME --output data.json --include-private
"""

import argparse
import importlib
import inspect
import json
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ParameterInfo:
    """Information about a function parameter"""

    name: str
    kind: str  # POSITIONAL_ONLY, POSITIONAL_OR_KEYWORD, VAR_POSITIONAL, etc.
    annotation: str | None = None
    default: str | None = None

    def to_dict(self) -> dict:
        result = {"name": self.name, "kind": self.kind}
        if self.annotation:
            result["annotation"] = self.annotation
        if self.default is not None:
            result["default"] = self.default
        return result


@dataclass
class FunctionInfo:
    """Information about a function or method"""

    name: str
    qualified_name: str
    signature_string: str
    docstring: str | None
    parameters: list[ParameterInfo]
    return_annotation: str | None = None
    is_async: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    class_name: str | None = None
    module_name: str | None = None

    def to_dict(self) -> dict:
        result = {
            "name": self.name,
            "qualified_name": self.qualified_name,
            "signature_string": self.signature_string,
            "docstring": self.docstring,
            "parameters": [p.to_dict() for p in self.parameters],
        }
        if self.return_annotation:
            result["return_annotation"] = self.return_annotation
        if self.is_async:
            result["is_async"] = True
        if self.is_classmethod:
            result["is_classmethod"] = True
        if self.is_staticmethod:
            result["is_staticmethod"] = True
        if self.class_name:
            result["class_name"] = self.class_name
        if self.module_name:
            result["module_name"] = self.module_name
        return result


@dataclass
class ClassInfo:
    """Information about a class"""

    name: str
    qualified_name: str
    docstring: str | None
    methods: list[FunctionInfo]
    bases: list[str]
    module_name: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "qualified_name": self.qualified_name,
            "docstring": self.docstring,
            "methods": [m.to_dict() for m in self.methods],
            "bases": self.bases,
            "module_name": self.module_name,
        }


@dataclass
class ModuleInfo:
    """Information about a module"""

    name: str
    docstring: str | None
    classes: list[ClassInfo]
    functions: list[FunctionInfo]
    submodules: list["ModuleInfo"]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "docstring": self.docstring,
            "classes": [c.to_dict() for c in self.classes],
            "functions": [f.to_dict() for f in self.functions],
            "submodules": [m.to_dict() for m in self.submodules],
        }


class ModuleIntrospector:
    """Introspects Python modules to extract API information"""

    def __init__(self, include_private: bool = False, max_depth: int = 3):
        self.include_private = include_private
        self.max_depth = max_depth
        self.visited_modules: set[str] = set()

    def should_include(self, name: str) -> bool:
        """Check if an object should be included based on naming"""
        if self.include_private:
            return True
        return not name.startswith("_")

    def format_annotation(self, annotation: Any) -> str | None:
        """Format a type annotation as a string"""
        if annotation is inspect.Parameter.empty:
            return None
        try:
            # Handle typing module annotations
            if hasattr(annotation, "__module__") and annotation.__module__ == "typing":
                return str(annotation)
            # Handle class types
            if inspect.isclass(annotation):
                return annotation.__name__
            # Fallback to string representation
            return str(annotation)
        except Exception:
            return str(annotation)

    def extract_parameters(self, sig: inspect.Signature) -> list[ParameterInfo]:
        """Extract parameter information from a signature"""
        parameters = []
        for param in sig.parameters.values():
            param_info = ParameterInfo(
                name=param.name,
                kind=param.kind.name,
                annotation=self.format_annotation(param.annotation),
                default=repr(param.default)
                if param.default is not inspect.Parameter.empty
                else None,
            )
            parameters.append(param_info)
        return parameters

    def introspect_function(
        self, func: Any, class_name: str | None = None, module_name: str | None = None
    ) -> FunctionInfo | None:
        """Introspect a function or method"""
        try:
            name = func.__name__
            if not self.should_include(name):
                return None

            # Get signature
            try:
                sig = inspect.signature(func)
                sig_string = str(sig)
                parameters = self.extract_parameters(sig)
                return_annotation = self.format_annotation(sig.return_annotation)
            except (ValueError, TypeError):
                # Can't get signature (C extension or built-in)
                sig_string = "(...)"
                parameters = []
                return_annotation = None

            # Get docstring
            docstring = inspect.getdoc(func)

            # Check if async
            is_async = inspect.iscoroutinefunction(func)

            # Check for classmethod/staticmethod
            is_classmethod = isinstance(func, classmethod)
            is_staticmethod = isinstance(func, staticmethod)

            # Build qualified name
            if class_name:
                qualified_name = (
                    f"{module_name}.{class_name}.{name}" if module_name else f"{class_name}.{name}"
                )
            else:
                qualified_name = f"{module_name}.{name}" if module_name else name

            return FunctionInfo(
                name=name,
                qualified_name=qualified_name,
                signature_string=sig_string,
                docstring=docstring,
                parameters=parameters,
                return_annotation=return_annotation,
                is_async=is_async,
                is_classmethod=is_classmethod,
                is_staticmethod=is_staticmethod,
                class_name=class_name,
                module_name=module_name,
            )

        except Exception as e:
            print(f"Warning: Could not introspect function {func}: {e}", file=sys.stderr)
            return None

    def introspect_class(self, cls: type, module_name: str | None = None) -> ClassInfo | None:
        """Introspect a class"""
        try:
            name = cls.__name__
            if not self.should_include(name):
                return None

            # Get docstring
            docstring = inspect.getdoc(cls)

            # Get base classes
            bases = [base.__name__ for base in cls.__bases__ if base is not object]

            # Get qualified name
            qualified_name = f"{module_name}.{name}" if module_name else name

            # Introspect methods
            methods = []
            for method_name, method in inspect.getmembers(cls, inspect.isfunction):
                if self.should_include(method_name):
                    method_info = self.introspect_function(
                        method, class_name=name, module_name=module_name
                    )
                    if method_info:
                        methods.append(method_info)

            # Also check for classmethods and staticmethods
            for method_name, method in inspect.getmembers(cls, inspect.ismethod):
                if self.should_include(method_name):
                    method_info = self.introspect_function(
                        method, class_name=name, module_name=module_name
                    )
                    if method_info and method_info not in methods:
                        methods.append(method_info)

            return ClassInfo(
                name=name,
                qualified_name=qualified_name,
                docstring=docstring,
                methods=methods,
                bases=bases,
                module_name=module_name,
            )

        except Exception as e:
            print(f"Warning: Could not introspect class {cls}: {e}", file=sys.stderr)
            return None

    def introspect_module(self, module: Any, depth: int = 0) -> ModuleInfo | None:
        """Introspect a module"""
        try:
            module_name = module.__name__

            # Check if already visited or max depth reached
            if module_name in self.visited_modules or depth > self.max_depth:
                return None

            self.visited_modules.add(module_name)

            print(f"Introspecting module: {module_name} (depth {depth})", file=sys.stderr)

            # Get docstring
            docstring = inspect.getdoc(module)

            # Introspect classes
            classes = []
            for cls_name, cls in inspect.getmembers(module, inspect.isclass):
                # Only include classes defined in this module
                if (
                    self.should_include(cls_name)
                    and hasattr(cls, "__module__")
                    and cls.__module__ == module_name
                ):
                    class_info = self.introspect_class(cls, module_name=module_name)
                    if class_info:
                        classes.append(class_info)

            # Introspect functions
            functions = []
            for func_name, func in inspect.getmembers(module, inspect.isfunction):
                # Only include functions defined in this module
                if (
                    self.should_include(func_name)
                    and hasattr(func, "__module__")
                    and func.__module__ == module_name
                ):
                    func_info = self.introspect_function(func, module_name=module_name)
                    if func_info:
                        functions.append(func_info)

            # Introspect submodules
            submodules = []
            if depth < self.max_depth:
                for submodule_name, submodule in inspect.getmembers(module, inspect.ismodule):
                    # Only include submodules that are part of this package
                    if (
                        self.should_include(submodule_name)
                        and hasattr(submodule, "__name__")
                        and submodule.__name__.startswith(module_name)
                    ):
                        submodule_info = self.introspect_module(submodule, depth=depth + 1)
                        if submodule_info:
                            submodules.append(submodule_info)

            return ModuleInfo(
                name=module_name,
                docstring=docstring,
                classes=classes,
                functions=functions,
                submodules=submodules,
            )

        except Exception as e:
            print(f"Warning: Could not introspect module {module}: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return None


def main():
    parser = argparse.ArgumentParser(
        description="Introspect a Python module and output structured JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("module", help="Name of the module to introspect")
    parser.add_argument("--output", "-o", required=True, help="Output JSON file path")
    parser.add_argument(
        "--include-private", action="store_true", help="Include private members (starting with _)"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum depth for submodule introspection (default: 3)",
    )

    args = parser.parse_args()

    # Import the module
    try:
        print(f"Importing module: {args.module}", file=sys.stderr)
        module = importlib.import_module(args.module)
    except ImportError as e:
        print(f"Error: Could not import module '{args.module}': {e}", file=sys.stderr)
        sys.exit(1)

    # Introspect the module
    introspector = ModuleIntrospector(
        include_private=args.include_private, max_depth=args.max_depth
    )

    module_info = introspector.introspect_module(module)

    if not module_info:
        print(f"Error: Failed to introspect module '{args.module}'", file=sys.stderr)
        sys.exit(1)

    # Save to JSON
    output_path = Path(args.output)
    print(f"Writing output to: {output_path}", file=sys.stderr)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(module_info.to_dict(), f, indent=2, ensure_ascii=False)

    # Print statistics
    def count_stats(mod_info):
        classes_count = len(mod_info["classes"])
        functions_count = len(mod_info["functions"])
        methods_count = sum(len(c["methods"]) for c in mod_info["classes"])
        submodules_count = len(mod_info["submodules"])

        for submod in mod_info["submodules"]:
            sub_stats = count_stats(submod)
            classes_count += sub_stats[0]
            functions_count += sub_stats[1]
            methods_count += sub_stats[2]
            submodules_count += sub_stats[3]

        return classes_count, functions_count, methods_count, submodules_count

    classes, functions, methods, submodules = count_stats(module_info.to_dict())

    print("\nIntrospection complete!", file=sys.stderr)
    print(f"  Modules: {submodules + 1}", file=sys.stderr)
    print(f"  Classes: {classes}", file=sys.stderr)
    print(f"  Functions: {functions}", file=sys.stderr)
    print(f"  Methods: {methods}", file=sys.stderr)
    print(f"  Total functions: {functions + methods}", file=sys.stderr)


if __name__ == "__main__":
    main()
