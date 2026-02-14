"""
Tests for main entry point and core system functionality.

Run with: pytest tests/test_main.py -v
"""

import pytest
from pathlib import Path
import sys

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# BASIC SANITY TESTS
# ============================================================

def test_hello_world():
    """Basic sanity check."""
    assert 1 + 1 == 2


# ============================================================
# CONFIG IMPORT TESTS
# ============================================================

def test_config_imports():
    """Test that all config variables can be imported."""
    from core.config import (
        OLLAMA_HOST,
        OLLAMA_MODEL,
        OLLAMA_EMBEDDING_MODEL,
        OLLAMA_COMPLETION_MODEL,
        LLM_TEMPERATURE,
        COMPLETION_TEMPERATURE,
        COMPLETION_MAX_TOKENS,
        ENABLE_INLINE_COMPLETION,
        DEFAULT_API_KEY,
        PROJECT_ROOT,
    )
    
    assert OLLAMA_HOST is not None
    assert OLLAMA_MODEL is not None
    assert isinstance(LLM_TEMPERATURE, float)
    assert isinstance(COMPLETION_TEMPERATURE, float)
    assert isinstance(COMPLETION_MAX_TOKENS, int)
    assert isinstance(ENABLE_INLINE_COMPLETION, bool)
    assert DEFAULT_API_KEY is not None


def test_config_defaults():
    """Test that config has sensible defaults."""
    from core.config import (
        LLM_TEMPERATURE,
        COMPLETION_TEMPERATURE,
        COMPLETION_MAX_TOKENS,
        MAX_RETRIES,
    )
    
    # Temperature should be between 0 and 1
    assert 0 <= LLM_TEMPERATURE <= 1
    assert 0 <= COMPLETION_TEMPERATURE <= 1
    
    # Tokens should be positive
    assert COMPLETION_MAX_TOKENS > 0
    
    # Retries should be reasonable
    assert 1 <= MAX_RETRIES <= 10


# ============================================================
# CORE MODULE IMPORT TESTS
# ============================================================

def test_models_import():
    """Test that Pydantic models can be imported."""
    from core.models import (
        PlanResponse,
        ExecutorResponse,
        ReviewResponse,
        TypeCheckResult,
        TestExecutionResult,
    )
    
    assert PlanResponse is not None
    assert ExecutorResponse is not None
    assert ReviewResponse is not None


def test_llm_functions_import():
    """Test that LLM functions can be imported."""
    from core.llm import (
        call_llm,
        extract_json,
        get_code_completions,
        get_single_completion,
    )
    
    assert callable(call_llm)
    assert callable(extract_json)
    assert callable(get_code_completions)
    assert callable(get_single_completion)


def test_chat_interface_v2_import():
    """Test that chat interface v2 can be imported."""
    from core.chat_interface import (
        ContinueDEVServer,
        ChatRequest,
        ChatResponse,
        CompletionRequest,
        CompletionResponse,
    )
    
    assert ContinueDEVServer is not None
    assert ChatRequest is not None
    assert CompletionRequest is not None


# ============================================================
# AGENTS IMPORT TESTS
# ============================================================

def test_agents_import():
    """Test that core agents can be imported (skip optional dependencies)."""
    from agents.planner_agent import PlannerAgent
    from agents.executor_agent import ExecutorAgent
    from agents.reviewer_agent import ReviewerAgent
    from agents.memory_agent import MemoryAgent
    from agents.ci_cd_agent import CICDAgent
    from agents.type_checker_agent import TypeCheckerAgent
    from agents.static_analysis_agent import StaticAnalysisAgent
    from agents.test_agent import TestAgent
    from agents.cache_agent import CacheAgent
    from agents.error_pattern_agent import ErrorPatternAgent
    # ASTRefactorerAgent requires libcst which is optional
    
    assert PlannerAgent is not None
    assert ExecutorAgent is not None
    assert ReviewerAgent is not None


# ============================================================
# TOOLS IMPORT TESTS
# ============================================================

def test_tools_import():
    """Test that all tools can be imported."""
    from tools.filesystem_tool import (
        read_file,
        write_file,
        list_dir,
    )
    from tools.terminal_tool import run_cmd
    from tools.git_tool import git_status
    from tools.web_tool import fetch_url
    
    assert callable(read_file)
    assert callable(write_file)
    assert callable(list_dir)
    assert callable(run_cmd)
    assert callable(git_status)
    assert callable(fetch_url)


# ============================================================
# JSON EXTRACTION TESTS
# ============================================================

def test_extract_json_from_markdown():
    """Test JSON extraction from markdown code blocks."""
    from core.llm import extract_json
    
    text = '''Here is the result:
```json
{"key": "value", "number": 42}
```
That's the answer.'''
    
    result = extract_json(text)
    assert result == {"key": "value", "number": 42}


def test_extract_json_raw():
    """Test JSON extraction from raw text."""
    from core.llm import extract_json
    
    text = 'The answer is {"status": "ok", "count": 5} as expected.'
    
    result = extract_json(text)
    assert result == {"status": "ok", "count": 5}


def test_extract_json_nested():
    """Test JSON extraction with nested objects."""
    from core.llm import extract_json
    
    text = '''{"outer": {"inner": {"deep": true}}, "list": [1, 2, 3]}'''
    
    result = extract_json(text)
    assert result["outer"]["inner"]["deep"] is True
    assert result["list"] == [1, 2, 3]


def test_extract_json_invalid():
    """Test JSON extraction with invalid input."""
    import json
    from core.llm import extract_json
    
    with pytest.raises(json.JSONDecodeError):
        extract_json("This has no JSON at all")


# ============================================================
# LANGUAGE REGISTRY TESTS
# ============================================================

def test_language_registry():
    """Test language registry functionality."""
    from core.language_registry import LanguageRegistry, Language
    
    registry = LanguageRegistry()
    
    # Test extension detection
    assert registry.get_language_by_extension(".py") == Language.PYTHON
    assert registry.get_language_by_extension(".ts") == Language.TYPESCRIPT
    assert registry.get_language_by_extension(".js") == Language.JAVASCRIPT
    assert registry.get_language_by_extension(".go") == Language.GO
    assert registry.get_language_by_extension(".rs") == Language.RUST
    
    # Test config retrieval
    python_config = registry.get_config(Language.PYTHON)
    assert python_config is not None
    assert "pylint" in python_config.linters
    assert "mypy" in python_config.type_checkers


# ============================================================
# COMPLETION FUNCTION TESTS (Mocked)
# ============================================================

def test_clean_completion():
    """Test completion cleaning function."""
    from core.llm import _clean_completion
    
    # Test markdown removal
    text = "```python\nprint('hello')\n```"
    cleaned = _clean_completion(text, "py")
    assert "```" not in cleaned
    assert "print" in cleaned
    
    # Test clean text passes through
    clean_text = "return x + y"
    assert _clean_completion(clean_text, "py") == clean_text