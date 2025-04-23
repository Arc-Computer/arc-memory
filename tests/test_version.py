"""Test version information."""

import re

import arc_memory


def test_version():
    """Test that the version follows the expected format."""
    assert hasattr(arc_memory, "__version__")
    assert isinstance(arc_memory.__version__, str)
    assert re.match(r"^\d+\.\d+\.\d+b\d{8}$", arc_memory.__version__)
