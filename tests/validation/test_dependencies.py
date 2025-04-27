"""Tests for dependency validation."""

import sys
import unittest
from unittest.mock import patch

from arc_memory.dependencies import (
    check_dependency,
    check_dependencies,
    check_python_version,
    validate_dependencies,
    validate_python_version,
)
from arc_memory.errors import DependencyError


class TestDependencyValidation(unittest.TestCase):
    """Tests for dependency validation functions."""

    def test_check_dependency_installed(self):
        """Test checking if an installed dependency is available."""
        # sys is always available in Python
        self.assertTrue(check_dependency("sys"))

    def test_check_dependency_not_installed(self):
        """Test checking if a non-existent dependency is available."""
        self.assertFalse(check_dependency("non_existent_package_12345"))

    def test_check_dependencies(self):
        """Test checking multiple dependencies."""
        with patch("arc_memory.dependencies.check_dependency") as mock_check:
            # Mock all dependencies as installed
            mock_check.return_value = True
            success, missing = check_dependencies()
            self.assertTrue(success)
            self.assertEqual(missing, {})

            # Mock one core dependency as missing
            def side_effect(name):
                return name != "networkx"

            mock_check.side_effect = side_effect
            success, missing = check_dependencies()
            self.assertFalse(success)
            self.assertIn("core", missing)
            self.assertIn("networkx", missing["core"])

            # Test with optional dependencies
            success, missing = check_dependencies(include_optional=True)
            self.assertFalse(success)
            self.assertIn("core", missing)

            # Test without optional dependencies
            mock_check.reset_mock()
            mock_check.return_value = True
            mock_check.side_effect = None  # Clear the side effect
            success, missing = check_dependencies(include_optional=False)
            self.assertTrue(success)
            self.assertEqual(missing, {})

    def test_validate_dependencies(self):
        """Test validating dependencies with error raising."""
        with patch("arc_memory.dependencies.check_dependencies") as mock_check:
            # All dependencies installed
            mock_check.return_value = (True, {})
            result = validate_dependencies()
            self.assertEqual(result, {})

            # Missing core dependencies, but don't raise error
            mock_check.return_value = (False, {"core": ["networkx"]})
            result = validate_dependencies(raise_error=False)
            self.assertEqual(result, {"core": ["networkx"]})

            # Missing core dependencies, raise error
            with self.assertRaises(DependencyError) as context:
                validate_dependencies(raise_error=True)
            self.assertIn("Missing required core dependencies", str(context.exception))
            self.assertIn("networkx", str(context.exception))

            # Missing optional dependencies, don't raise error
            mock_check.return_value = (False, {"github": ["pyjwt"]})
            result = validate_dependencies(raise_error=True)
            self.assertEqual(result, {"github": ["pyjwt"]})

    def test_check_python_version(self):
        """Test checking Python version."""
        # Current version should be valid
        current_version = sys.version_info[:3]
        self.assertTrue(check_python_version(current_version))

        # Future version should be invalid
        future_version = (sys.version_info[0] + 1, 0, 0)
        self.assertFalse(check_python_version(future_version))

    def test_validate_python_version(self):
        """Test validating Python version with error raising."""
        # Current version should be valid
        current_version = sys.version_info[:3]
        self.assertTrue(validate_python_version(current_version))

        # Future version should be invalid
        future_version = (sys.version_info[0] + 1, 0, 0)
        with self.assertRaises(DependencyError) as context:
            validate_python_version(future_version)
        self.assertIn("Python version", str(context.exception))
        self.assertIn("too old", str(context.exception))

        # Don't raise error
        self.assertFalse(validate_python_version(future_version, raise_error=False))


if __name__ == "__main__":
    unittest.main()
