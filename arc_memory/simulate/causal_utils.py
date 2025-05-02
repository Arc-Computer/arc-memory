"""Utility functions for causal analysis in Arc Memory simulations.

This module provides utility functions for causal analysis, including
building causal graphs and analyzing causal relationships.
"""

import logging
from typing import Dict, List, Any, Optional

from arc_memory.simulate.causal_graph import build_causal_graph

logger = logging.getLogger(__name__)

# Re-export the build_causal_graph function for backward compatibility
__all__ = ["build_causal_graph"]
