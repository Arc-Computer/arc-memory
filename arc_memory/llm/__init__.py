"""LLM integration for Arc Memory.

This module provides integration with language models for enhancing
the knowledge graph with semantic understanding and reasoning.
"""

from arc_memory.llm.ollama_client import OllamaClient, ensure_ollama_available

# Import OpenAI client conditionally to avoid hard dependency
try:
    from arc_memory.llm.openai_client import OpenAIClient, ensure_openai_available
    OPENAI_AVAILABLE = True
    __all__ = ["OllamaClient", "ensure_ollama_available", "OpenAIClient", "ensure_openai_available"]
except ImportError:
    OPENAI_AVAILABLE = False
    __all__ = ["OllamaClient", "ensure_ollama_available"]
