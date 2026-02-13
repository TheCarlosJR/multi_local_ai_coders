"""
Core package - funções centrais do sistema
"""

from .config import logger, validate_config, OLLAMA_HOST, OLLAMA_MODEL
from .llm import call_llm, extract_json, call_llm_stream

__all__ = [
    "logger",
    "validate_config",
    "call_llm",
    "extract_json",
    "call_llm_stream",
    "run",  # Import explicitly: from core.agent_runner import run
]
