"""Tests for introspect.py script."""

import json

import pytest

# Import the introspect module
from scripts.introspect import (
    ModuleIntrospector,
    ParameterInfo,
)


class TestParameterInfo:
    """Tests for ParameterInfo dataclass."""

    def test_creation(self):
        """Test creating a ParameterInfo."""
        param = ParameterInfo(
            name="test_param",
            kind="POSITIONAL_OR_KEYWORD",
            annotation="int",
            default="5",
        )
        assert param.name == "test_param"
        assert param.kind == "POSITIONAL_OR_KEYWORD"
        assert param.annotation == "int"
        assert param.default == "5"

    def test_to_dict(self):
        """Test converting ParameterInfo to dict."""
        param = ParameterInfo(name="x", kind="POSITIONAL_OR_KEYWORD", annotation="str")
        result = param.to_dict()
        assert result["name"] == "x"
        assert result["kind"] == "POSITIONAL_OR_KEYWORD"
        assert result["annotation"] == "str"
        assert "default" not in result

    def test_to_dict_with_default(self):
        """Test to_dict with default value."""
        param = ParameterInfo(
            name="y", kind="POSITIONAL_OR_KEYWORD", annotation="int", default="10"
        )
        result = param.to_dict()
        assert result["default"] == "10"


class TestModuleIntrospector:
    """Tests for ModuleIntrospector class."""

    def test_should_include_public(self):
        """Test should_include for public names."""
        introspector = ModuleIntrospector(include_private=False)
        assert introspector.should_include("public_name")
        assert introspector.should_include("PublicClass")

    def test_should_include_private(self):
        """Test should_include for private names."""
        introspector = ModuleIntrospector(include_private=False)
        assert not introspector.should_include("_private")
        assert not introspector.should_include("__dunder__")

    def test_should_include_with_flag(self):
        """Test should_include with include_private=True."""
        introspector = ModuleIntrospector(include_private=True)
        assert introspector.should_include("_private")
        assert introspector.should_include("public")

    def test_format_annotation_none(self):
        """Test format_annotation with no annotation."""
        introspector = ModuleIntrospector()
        import inspect

        result = introspector.format_annotation(inspect.Parameter.empty)
        assert result is None

    def test_format_annotation_class(self):
        """Test format_annotation with class type."""
        introspector = ModuleIntrospector()
        result = introspector.format_annotation(int)
        assert result == "int"

    def test_introspect_simple_module(self):
        """Test introspecting a simple built-in module."""
        introspector = ModuleIntrospector(include_private=False, max_depth=1)
        import json as test_module

        result = introspector.introspect_module(test_module)

        assert result is not None
        assert result.name == "json"
        assert result.docstring is not None
        assert len(result.functions) > 0  # json has functions like loads, dumps

    @pytest.mark.unit
    def test_visited_modules_tracking(self):
        """Test that visited modules are tracked."""
        introspector = ModuleIntrospector()
        import json as test_module

        introspector.introspect_module(test_module)
        assert "json" in introspector.visited_modules

    @pytest.mark.unit
    def test_max_depth_limit(self):
        """Test that max_depth is respected."""
        introspector = ModuleIntrospector(max_depth=0)
        import json as test_module

        result = introspector.introspect_module(test_module, depth=1)
        # Should return None because depth > max_depth
        assert result is None


class TestIntegration:
    """Integration tests for the introspection system."""

    @pytest.mark.integration
    def test_introspect_json_module(self):
        """Test introspecting the json module."""
        introspector = ModuleIntrospector(include_private=False, max_depth=1)
        import json as test_module

        result = introspector.introspect_module(test_module)

        assert result is not None
        assert result.name == "json"

        # Check for known functions
        function_names = [f.name for f in result.functions]
        assert "loads" in function_names or "dumps" in function_names

    @pytest.mark.integration
    def test_full_introspection_workflow(self, temp_dir):
        """Test complete introspection workflow."""
        introspector = ModuleIntrospector(include_private=False, max_depth=1)

        # Introspect json module
        import json as test_module

        result = introspector.introspect_module(test_module)
        assert result is not None

        # Convert to dict and save
        output_file = temp_dir / "test_output.json"
        with open(output_file, "w") as f:
            json.dump(result.to_dict(), f, indent=2)

        # Verify file was created and is valid JSON
        assert output_file.exists()

        with open(output_file) as f:
            data = json.load(f)

        assert data["name"] == "json"
        assert "functions" in data
        assert isinstance(data["functions"], list)
