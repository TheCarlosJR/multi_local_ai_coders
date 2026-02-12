"""
Prompts package - templates de prompts para os agentes
"""

from .base_prompt import BASE_SYSTEM_PROMPT
from .planner_prompt import PLANNER_PROMPT
from .executor_prompt import EXECUTOR_PROMPT
from .reviewer_prompt import REVIEWER_PROMPT
from .memory_retrieval_prompt import MEMORY_RETRIEVAL_PROMPT
from .error_recovery_prompt import ERROR_RECOVERY_PROMPT

__all__ = [
    "BASE_SYSTEM_PROMPT",
    "PLANNER_PROMPT",
    "EXECUTOR_PROMPT",
    "REVIEWER_PROMPT",
    "MEMORY_RETRIEVAL_PROMPT",
    "ERROR_RECOVERY_PROMPT",
]
