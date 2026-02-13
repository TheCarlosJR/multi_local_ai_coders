"""
Intelligent Context Management for LLM

Handles:
- Sliding window of LLM context size
- Semantic compression when context exceeds limits
- Priority-based memory injection (recent > relevant > common)
- Token counting and budget management

Installation:
    pip install tiktoken  # For token counting
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

from core.config import OLLAMA_MODEL
from core.structured_logger import get_logger

logger = get_logger(__name__)


class TokenBudget(Enum):
    """Token allocation per model."""
    QWEN_14B = 8000
    QWEN_32B = 32000
    MISTRAL_7B = 8000
    NEURAL_CHAT_7B = 4000
    CUSTOM = 4000  # Default


class ContextManager:
    """Manage LLM context window intelligently."""
    
    # Budget allocation (percentages of context window)
    SYSTEM_PROMPT_PCT = 0.20  # 20% for system prompt
    INPUT_PCT = 0.50  # 50% for user input
    OUTPUT_PCT = 0.20  # 20% reserved for output
    MEMORY_PCT = 0.10  # 10% for injected memories
    
    def __init__(self, model_name: str = OLLAMA_MODEL):
        self.logger = get_logger(__name__)
        self.model_name = model_name
        self.token_budget = self._get_token_budget(model_name)
        self.tokenizer = self._get_tokenizer() if TIKTOKEN_AVAILABLE else None
        
        # Calculate budgets
        self.system_budget = int(self.token_budget * self.SYSTEM_PROMPT_PCT)
        self.input_budget = int(self.token_budget * self.INPUT_PCT)
        self.output_budget = int(self.token_budget * self.OUTPUT_PCT)
        self.memory_budget = int(self.token_budget * self.MEMORY_PCT)
        
        self.logger.info(
            f"✓ Context manager initialized for {model_name} "
            f"({self.token_budget} tokens total budget)"
        )
    
    def prepare_context(
        self,
        system_prompt: str,
        user_prompt: str,
        injected_memories: Optional[List[str]] = None,
        project_context: Optional[str] = None,
    ) -> Tuple[str, str, Dict[str, int]]:
        """
        Prepare final system and user prompts respecting budget.
        
        Args:
            system_prompt: Base system prompt
            user_prompt: User input
            injected_memories: List of retrieved memories to inject
            project_context: Project understanding summary
        
        Returns:
            (final_system_prompt, final_user_prompt, tokens_used)
        """
        
        # Count tokens
        system_tokens = self._count_tokens(system_prompt)
        user_tokens = self._count_tokens(user_prompt)
        
        # Check if fits within budget
        if system_tokens > self.system_budget:
            self.logger.warning(
                f"System prompt exceeds budget: {system_tokens} > {self.system_budget}"
            )
            system_prompt = self._truncate_to_tokens(system_prompt, self.system_budget)
        
        if user_tokens > self.input_budget:
            self.logger.warning(
                f"User prompt exceeds budget: {user_tokens} > {self.input_budget}"
            )
            user_prompt = self._truncate_to_tokens(user_prompt, self.input_budget)
        
        # Inject memories and project context
        injected_text = self._build_injection(
            injected_memories,
            project_context,
            self.memory_budget,
        )
        
        # Combine
        final_system = f"{system_prompt}\n\n{injected_text}"
        final_user = user_prompt
        
        tokens_used = {
            "system": self._count_tokens(final_system),
            "user": self._count_tokens(final_user),
            "total": self._count_tokens(final_system) + self._count_tokens(final_user),
            "budget": self.token_budget,
        }
        
        # Warn if approaching limit
        if tokens_used["total"] > self.token_budget * 0.9:
            self.logger.warning(
                f"Approaching context limit: {tokens_used['total']}/{self.token_budget} tokens"
            )
        
        return final_system, final_user, tokens_used
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        
        if not TIKTOKEN_AVAILABLE or not self.tokenizer:
            # Fallback: rough estimate (1 token ≈ 4 chars)
            return len(text) // 4
        
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            self.logger.debug(f"Token counting error: {e}")
            return len(text) // 4
    
    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit."""
        
        if not TIKTOKEN_AVAILABLE or not self.tokenizer:
            # Fallback: rough estimate
            max_chars = max_tokens * 4
            if len(text) > max_chars:
                return text[:max_chars] + "\n... [truncated]"
            return text
        
        try:
            tokens = self.tokenizer.encode(text)
            if len(tokens) > max_tokens:
                tokens = tokens[:max_tokens]
                decoded = self.tokenizer.decode(tokens)
                return decoded + "\n... [truncated]"
            return text
        except Exception as e:
            self.logger.debug(f"Truncation error: {e}")
            return text
    
    def _get_token_budget(self, model_name: str) -> int:
        """Get default token budget for model."""
        
        model_lower = model_name.lower()
        
        if "32b" in model_lower or "32k" in model_lower:
            return TokenBudget.QWEN_32B.value
        elif "qwen" in model_lower:
            return TokenBudget.QWEN_14B.value
        elif "mistral" in model_lower:
            return TokenBudget.MISTRAL_7B.value
        elif "neural" in model_lower:
            return TokenBudget.NEURAL_CHAT_7B.value
        else:
            self.logger.warning(f"Unknown model {model_name}, using default budget")
            return TokenBudget.CUSTOM.value
    
    def _get_tokenizer(self):
        """Get tiktoken tokenizer."""
        
        try:
            # Try GPT-3.5 encoding (similar to most models)
            return tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            self.logger.warning(f"Could not initialize tiktoken: {e}")
            return None
    
    def _build_injection(
        self,
        memories: Optional[List[str]],
        project_context: Optional[str],
        budget: int,
    ) -> str:
        """Build injection combining memories and project context."""
        
        injection = []
        remaining_budget = budget
        
        # Priority 1: Project understanding (most important)
        if project_context:
            project_tokens = self._count_tokens(project_context)
            if project_tokens <= remaining_budget * 0.6:
                injection.append(f"## Project Context\n{project_context}")
                remaining_budget -= project_tokens
        
        # Priority 2: Recent memories (by order - first is most recent)
        if memories:
            memories_text = "\n".join(f"- {mem}" for mem in memories[:5])  # Max 5 memories
            memories_tokens = self._count_tokens(memories_text)
            if memories_tokens <= remaining_budget:
                injection.append(f"## Recent Context\n{memories_text}")
                remaining_budget -= memories_tokens
        
        return "\n".join(injection)


class CompressionAdvisor:
    """Advises when and how to compress context."""
    
    COMPRESSION_THRESHOLD = 0.7  # Compress if >70% of budget used
    
    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager
        self.logger = get_logger(__name__)
    
    def should_compress(self, system: str, user: str) -> bool:
        """Check if compression needed."""
        
        total_tokens = (
            self.context_manager._count_tokens(system) +
            self.context_manager._count_tokens(user)
        )
        
        usage_ratio = total_tokens / self.context_manager.token_budget
        
        if usage_ratio > self.COMPRESSION_THRESHOLD:
            self.logger.info(
                f"Context compression recommended: {usage_ratio:.1%} of budget used"
            )
            return True
        
        return False
    
    def recommend_compression(self, text: str, target_reduction: float = 0.3) -> str:
        """
        Recommend text compression strategy.
        
        target_reduction: How much to reduce (0.3 = compress by 30%)
        """
        
        original_tokens = self.context_manager._count_tokens(text)
        target_tokens = int(original_tokens * (1 - target_reduction))
        
        self.logger.info(
            f"Compression recommendation: {original_tokens} → {target_tokens} tokens"
        )
        
        return self.context_manager._truncate_to_tokens(text, target_tokens)
