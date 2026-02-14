"""
PHASE 8: Error Pattern Learning Agent

Analyzes error patterns across executions, learns from solutions,
and suggests automatic fixes for recurring issues.

Features:
- Error pattern recognition (syntax, logic, type, runtime)
- Solution tracking and success rate calculation
- Automatic pattern-based corrections
- Error taxonomy building
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import hashlib
from pathlib import Path

from core.models import ErrorPattern, ErrorSolution, PatternAnalysis
from agents.memory_agent import MemoryAgent


class ErrorPatternAgent:
    """
    Learns from error patterns and suggests solutions.
    
    Maintains a database of:
    - Error patterns (signature, frequency, context)
    - Solutions tried (success rate, execution time)
    - Error taxonomy (categories, severity)
    """
    
    def __init__(self):
        self.memory_agent = MemoryAgent()
        self.error_patterns_file = Path("vector_store/error_patterns.json")
        self.error_patterns = self._load_patterns()
        self.error_taxonomy = {
            "SyntaxError": {"category": "syntax", "severity": "high", "recoverable": True},
            "TypeError": {"category": "type", "severity": "high", "recoverable": True},
            "NameError": {"category": "reference", "severity": "medium", "recoverable": True},
            "ImportError": {"category": "import", "severity": "high", "recoverable": True},
            "ModuleNotFoundError": {"category": "import", "severity": "high", "recoverable": True},
            "AttributeError": {"category": "attribute", "severity": "medium", "recoverable": True},
            "KeyError": {"category": "key", "severity": "medium", "recoverable": False},
            "IndexError": {"category": "index", "severity": "medium", "recoverable": False},
            "ValueError": {"category": "value", "severity": "medium", "recoverable": True},
            "ZeroDivisionError": {"category": "math", "severity": "low", "recoverable": False},
            "FileNotFoundError": {"category": "filesystem", "severity": "high", "recoverable": True},
            "PermissionError": {"category": "permission", "severity": "high", "recoverable": False},
            "RecursionError": {"category": "logic", "severity": "high", "recoverable": True},
            "TimeoutError": {"category": "timeout", "severity": "medium", "recoverable": True},
            "ConnectionError": {"category": "network", "severity": "medium", "recoverable": True},
            "JSONDecodeError": {"category": "parsing", "severity": "medium", "recoverable": True},
        }
    
    def _load_patterns(self) -> Dict:
        """Load error patterns from persistent storage."""
        if self.error_patterns_file.exists():
            try:
                with open(self.error_patterns_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading patterns: {e}")
                return {"patterns": [], "solutions": [], "stats": {}}
        return {"patterns": [], "solutions": [], "stats": {}}
    
    def _save_patterns(self):
        """Save error patterns to persistent storage."""
        try:
            with open(self.error_patterns_file, 'w') as f:
                json.dump(self.error_patterns, f, indent=2)
        except Exception as e:
            print(f"Error saving patterns: {e}")
    
    def _extract_error_signature(self, error_message: str) -> str:
        """
        Extract a normalized error signature from error message.
        
        Examples:
        - "NameError: name 'foo' is not defined" → "NameError"
        - "TypeError: expected str, got int" → "TypeError:type_mismatch"
        - "ImportError: No module named 'foo'" → "ImportError:module"
        """
        # Extract error type
        error_type = ""
        if "Error:" in error_message or "Exception:" in error_message:
            match = re.search(r"(\w+Error|\w+Exception):", error_message)
            if match:
                error_type = match.group(1)
        
        # Extract context signature
        context = ""
        if "NameError" in error_message:
            match = re.search(r"name '(\w+)' is not defined", error_message)
            context = "undefined_variable"
        elif "TypeError" in error_message:
            if "expected" in error_message or "got" in error_message:
                context = "type_mismatch"
            elif "argument" in error_message:
                context = "wrong_args"
        elif "ImportError" in error_message or "ModuleNotFoundError" in error_message:
            if "No module" in error_message:
                context = "missing_module"
            else:
                context = "import_error"
        elif "AttributeError" in error_message:
            context = "missing_attribute"
        elif "KeyError" in error_message:
            context = "missing_key"
        elif "IndexError" in error_message:
            context = "index_out_of_range"
        elif "ValueError" in error_message:
            context = "invalid_value"
        elif "SyntaxError" in error_message:
            context = "syntax"
        elif "FileNotFoundError" in error_message:
            context = "file_not_found"
        elif "JSONDecodeError" in error_message:
            context = "json_parse"
        
        signature = f"{error_type}:{context}" if context else error_type
        return signature
    
    def analyze_error(self, error_message: str, code_context: str = "", 
                     language: str = "python", goal: str = "") -> PatternAnalysis:
        """
        Analyze an error and find similar patterns with solutions.
        
        Args:
            error_message: Full error message/traceback
            code_context: Code snippet that caused error
            language: Programming language
            goal: Original goal/task
        
        Returns:
            PatternAnalysis with matched patterns and suggestions
        """
        signature = self._extract_error_signature(error_message)
        
        # Find similar patterns in database
        similar_patterns = self._find_similar_patterns(signature, language, 30)
        
        # Build pattern analysis
        analysis = PatternAnalysis(
            error_signature=signature,
            error_type=self._get_error_type(error_message),
            language=language,
            code_context=code_context,
            matched_patterns=similar_patterns,
            timestamp=datetime.now().isoformat()
        )
        
        # Get suggestions
        if similar_patterns:
            analysis.suggested_solutions = [
                self._build_solution(p) for p in similar_patterns[:3]
            ]
        
        # Calculate pattern frequency
        stats = self._get_pattern_stats(signature)
        analysis.pattern_frequency = stats.get("frequency", 0)
        analysis.success_rate = stats.get("success_rate", 0)
        
        # Store in memory for future retrieval
        self._store_pattern_in_memory(analysis)
        
        return analysis
    
    def _find_similar_patterns(self, signature: str, language: str, 
                              max_days: int = 30) -> List[Dict]:
        """Find similar error patterns in history."""
        similar = []
        cutoff_date = (datetime.now() - timedelta(days=max_days)).isoformat()
        
        for pattern in self.error_patterns.get("patterns", []):
            if pattern["signature"] == signature and pattern["language"] == language:
                if pattern.get("timestamp", "") > cutoff_date:
                    similar.append(pattern)
        
        # Sort by success rate of solutions
        similar.sort(key=lambda p: p.get("best_solution_success_rate", 0), reverse=True)
        return similar[:5]
    
    def _get_error_type(self, error_message: str) -> str:
        """Extract error type from message."""
        match = re.search(r"(\w+Error|\w+Exception)", error_message)
        return match.group(1) if match else "UnknownError"
    
    def _build_solution(self, pattern: Dict) -> ErrorSolution:
        """Convert pattern to solution object."""
        solutions = pattern.get("solutions", [])
        if not solutions:
            return ErrorSolution(
                description="No known solutions yet",
                success_rate=0,
                fix_type="manual"
            )
        
        best = max(solutions, key=lambda s: s.get("success_rate", 0))
        return ErrorSolution(
            description=best.get("description", ""),
            fix_type=best.get("type", "manual"),
            code_fix=best.get("code_fix", ""),
            success_rate=best.get("success_rate", 0),
            attempts=best.get("attempts", 0)
        )
    
    def _get_pattern_stats(self, signature: str) -> Dict:
        """Get statistics for a pattern."""
        stats = self.error_patterns.get("stats", {})
        return stats.get(signature, {"frequency": 0, "success_rate": 0})
    
    def _store_pattern_in_memory(self, analysis: PatternAnalysis):
        """Store analysis in vector store for semantic search."""
        memory_entry = {
            "type": "error_pattern",
            "signature": analysis.error_signature,
            "language": analysis.language,
            "description": f"Error pattern: {analysis.error_type} in {analysis.language}",
            "frequency": analysis.pattern_frequency,
            "success_rate": analysis.success_rate,
            "timestamp": analysis.timestamp
        }
        
        # Store in memory for RAG retrieval
        try:
            self.memory_agent.add_to_memory(
                content=json.dumps(memory_entry),
                metadata=memory_entry
            )
        except Exception as e:
            print(f"Error storing pattern in memory: {e}")
    
    def record_error(self, error_message: str, code: str, language: str, 
                    goal: str, fix_applied: Optional[str] = None,
                    fix_successful: bool = False):
        """
        Record an error and whether the fix worked.
        
        Args:
            error_message: Error message/traceback
            code: Code that caused error
            language: Programming language
            goal: Original goal
            fix_applied: Fix that was attempted
            fix_successful: Whether fix resolved the error
        """
        signature = self._extract_error_signature(error_message)
        
        # Find or create pattern
        pattern = self._find_pattern_by_signature(signature, language)
        if not pattern:
            pattern = {
                "signature": signature,
                "language": language,
                "error_type": self._get_error_type(error_message),
                "first_seen": datetime.now().isoformat(),
                "frequency": 0,
                "solutions": [],
                "code_samples": []
            }
            self.error_patterns["patterns"].append(pattern)
        
        # Update frequency
        pattern["frequency"] = pattern.get("frequency", 0) + 1
        pattern["timestamp"] = datetime.now().isoformat()
        
        # Record code sample
        if code:
            pattern["code_samples"].append({
                "code": code,
                "goal": goal,
                "timestamp": datetime.now().isoformat()
            })
        
        # Record solution if provided
        if fix_applied:
            self._record_solution(pattern, fix_applied, fix_successful)
        
        # Update statistics
        self._update_pattern_stats(signature)
        
        # Save to disk
        self._save_patterns()
    
    def _find_pattern_by_signature(self, signature: str, language: str) -> Optional[Dict]:
        """Find existing pattern by signature."""
        for pattern in self.error_patterns.get("patterns", []):
            if pattern["signature"] == signature and pattern["language"] == language:
                return pattern
        return None
    
    def _record_solution(self, pattern: Dict, fix: str, successful: bool):
        """Record a solution attempt for a pattern."""
        solutions = pattern.get("solutions", [])
        
        # Find or create this solution
        solution = None
        for s in solutions:
            if s.get("description") == fix:
                solution = s
                break
        
        if not solution:
            solution = {
                "description": fix,
                "type": self._classify_fix_type(fix),
                "attempts": 0,
                "successes": 0,
                "success_rate": 0
            }
            solutions.append(solution)
        
        # Update statistics
        solution["attempts"] = solution.get("attempts", 0) + 1
        if successful:
            solution["successes"] = solution.get("successes", 0) + 1
        
        solution["success_rate"] = (
            solution["successes"] / solution["attempts"]
            if solution["attempts"] > 0 else 0
        )
        
        pattern["solutions"] = solutions
        pattern["best_solution_success_rate"] = max(
            [s.get("success_rate", 0) for s in solutions],
            default=0
        )
    
    def _classify_fix_type(self, fix: str) -> str:
        """Classify type of fix applied."""
        if "import" in fix.lower():
            return "import_fix"
        elif "type" in fix.lower() or "hint" in fix.lower():
            return "type_annotation"
        elif "rename" in fix.lower() or "variable" in fix.lower():
            return "refactor"
        elif "except" in fix.lower() or "try" in fix.lower():
            return "error_handling"
        else:
            return "manual"
    
    def _update_pattern_stats(self, signature: str):
        """Update aggregate statistics for a pattern."""
        pattern = self._find_pattern_by_signature(signature, "")
        if not pattern:
            return
        
        stats = {
            "frequency": pattern.get("frequency", 0),
            "success_rate": pattern.get("best_solution_success_rate", 0),
            "last_seen": pattern.get("timestamp", ""),
            "num_solutions": len(pattern.get("solutions", []))
        }
        
        if "stats" not in self.error_patterns:
            self.error_patterns["stats"] = {}
        
        self.error_patterns["stats"][signature] = stats
    
    def get_top_recurring_errors(self, top_n: int = 10, 
                                language: Optional[str] = None) -> List[Dict]:
        """
        Get most frequently occurring errors.
        
        Args:
            top_n: How many top errors to return
            language: Filter by language (None = all)
        
        Returns:
            List of recurring error patterns with metadata
        """
        patterns = self.error_patterns.get("patterns", [])
        
        if language:
            patterns = [p for p in patterns if p.get("language") == language]
        
        # Sort by frequency
        patterns.sort(key=lambda p: p.get("frequency", 0), reverse=True)
        
        result = []
        for pattern in patterns[:top_n]:
            result.append({
                "signature": pattern.get("signature"),
                "error_type": pattern.get("error_type"),
                "language": pattern.get("language"),
                "frequency": pattern.get("frequency"),
                "success_rate": pattern.get("best_solution_success_rate", 0),
                "num_solutions": len(pattern.get("solutions", [])),
                "first_seen": pattern.get("first_seen"),
                "last_seen": pattern.get("timestamp")
            })
        
        return result
    
    def suggest_preemptive_fixes(self, code: str, language: str, goal: str) -> List[str]:
        """
        Suggest fixes based on code analysis before execution.
        
        Analyzes code for patterns that commonly cause errors.
        """
        suggestions = []
        
        if language == "python":
            # Check for common Python issues
            if "import " in code and ("json" in code or "requests" in code):
                if "except" not in code:
                    suggestions.append(
                        "Add try/except for JSON parsing or requests errors"
                    )
            
            if "open(" in code and "with" not in code:
                suggestions.append(
                    "Use 'with' statement for file operations to ensure cleanup"
                )
            
            if "split(" in code and "[0]" in code:
                suggestions.append(
                    "Check if split() returns enough elements before indexing"
                )
            
            if "dict[" in code or "list[" in code:
                suggestions.append(
                    "Add bounds/key checking before accessing with index/key"
                )
        
        return suggestions
    
    def get_error_taxonomy_for_language(self, language: str = "python") -> Dict:
        """Get error taxonomy filtered for a language."""
        return {
            k: v for k, v in self.error_taxonomy.items()
            if language in ["all", "python", "javascript", "typescript"]
        }
    
    def cleanup_old_patterns(self, retention_days: int = 90) -> int:
        """
        Remove error patterns older than retention days.
        
        Returns:
            Number of patterns removed
        """
        cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()
        original_count = len(self.error_patterns.get("patterns", []))
        
        self.error_patterns["patterns"] = [
            p for p in self.error_patterns.get("patterns", [])
            if p.get("timestamp", "") > cutoff_date
        ]
        
        removed = original_count - len(self.error_patterns.get("patterns", []))
        self._save_patterns()
        
        return removed


# Export for use in agents
__all__ = ["ErrorPatternAgent"]
