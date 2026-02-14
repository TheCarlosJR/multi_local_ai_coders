"""
Enhanced Code Review Agent - Multi-Criteria Evaluation

Review Criteria:
1. Functional: Does it meet the requirement?
2. Security: No vulnerabilities, proper validation
3. Performance: Efficient algorithms, no memory leaks
4. Maintainability: Readable, well-documented, not too complex
5. Testing: Adequate test coverage, edge cases handled
6. Compliance: Follows coding standards, linting passes

Returns detailed report with scores for each criterion.
"""

import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from core.llm import call_llm, extract_json
from core.models import ReviewResponse, ReviewStatus
from core.diagnostics_engine import DiagnosticsEngine, Diagnostic, DiagnosticSeverity
from core.observability import SpanDecorator
from core.structured_logger import get_logger

logger = get_logger(__name__)


class ReviewCriterion(str, Enum):
    """Criteria for code review."""
    FUNCTIONAL = "functional"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    TESTING = "testing"
    COMPLIANCE = "compliance"


@dataclass
class CriterionScore:
    """Score for one criterion."""
    criterion: ReviewCriterion
    score: float  # 0.0-1.0
    passed: bool
    issues: List[str]
    suggestions: List[str]


class ReviewerAgent:
    """Enhanced code review with multi-criteria evaluation."""
    
    REVIEW_PROMPTS = {
        ReviewCriterion.FUNCTIONAL: """
Evaluate if the code FUNCTIONALLY solves the requirement.
Return JSON with:
- score: 0-100 (100=fully works, 0=doesn't work)
- passed: bool
- issues: list of functional problems
- suggestions: list to improve functionality

Requirement: {requirement}
Code/Result: {code}

JSON:
""",
        
        ReviewCriterion.SECURITY: """
Evaluate SECURITY:
- No hardcoded secrets or credentials
- Input validation and sanitization
- Protection against injection attacks (SQL, XSS, etc)
- Secure authentication/authorization
- No insecure dependencies (if applicable)

Return JSON with:
- score: 0-100
- passed: bool
- issues: list of security vulnerabilities
- suggestions: security improvements

Code: {code}

JSON:
""",
        
        ReviewCriterion.PERFORMANCE: """
Evaluate PERFORMANCE:
- Algorithm efficiency (Big-O complexity)
- No memory leaks or inefficient resource usage
- Appropriate data structures
- Caching opportunities
- Database query optimization (if applicable)

Return JSON with:
- score: 0-100
- passed: bool
- issues: performance problems detected
- suggestions: performance optimizations

Code: {code}

JSON:
""",
        
        ReviewCriterion.MAINTAINABILITY: """
Evaluate MAINTAINABILITY:
- Readable variable, function, class names
- Code length and complexity (functions < 30 lines, cyclomatic < 10)
- Presence of documentation/comments
- Follows DRY principle
- Modularity and separation of concerns

Return JSON with:
- score: 0-100
- passed: bool
- issues: maintainability problems
- suggestions: improvements

Code: {code}

JSON:
""",
        
        ReviewCriterion.TESTING: """
Evaluate TESTING:
- Test coverage goals (>80% for critical code)
- Edge cases are handled and tested
- Error cases covered
- Integration tests present (if applicable)
- Mocks/stubs appropriately used

Return JSON with:
- score: 0-100
- passed: bool
- issues: missing or inadequate tests
- suggestions: testing improvements

Code: {code}

JSON:
""",
        
        ReviewCriterion.COMPLIANCE: """
Evaluate STYLE & COMPLIANCE:
- Language conventions followed
- Coding standards (PEP8 for Python, etc)
- Linting warnings (stylistic, not errors)
- Consistent formatting
- Proper error handling patterns

Return JSON with:
- score: 0-100
- passed: bool
- issues: style/compliance problems
- suggestions: fixes

Code: {code}

JSON:
""",
    }
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.diagnostics_engine = DiagnosticsEngine()
    
    @SpanDecorator("reviewer.review_v2")
    def review(
        self,
        goal: str,
        code: str,
        file_path: Optional[str] = None,
    ) -> ReviewResponse:
        """
        Comprehensive code review using multi-criteria evaluation.
        
        Args:
            goal: Original requirement/goal
            code: Code to review (or execution result)
            file_path: If known, run diagnostics on it
        
        Returns:
            ReviewResponse with detailed scores
        """
        
        self.logger.info(f"[REVIEWER] Starting v2 review for:\n{goal[:100]}...")
        
        # Run all criteria in parallel
        criterion_scores = {}
        for criterion in ReviewCriterion:
            score = self._evaluate_criterion(criterion, code, goal)
            criterion_scores[criterion] = score
        
        # Run diagnostics if file provided
        diagnostics = []
        if file_path:
            diagnostics = self.diagnostics_engine.analyze_file(file_path)
        
        # Calculate overall score
        overall_score = sum(
            s.score for s in criterion_scores.values()
        ) / len(criterion_scores)
        
        # Determine status
        if overall_score >= 85:
            status = ReviewStatus.APPROVED
        elif overall_score >= 65:
            status = ReviewStatus.NEEDS_REFINEMENT
        else:
            status = ReviewStatus.FAILED
        
        # Build issues and suggestions
        all_issues = []
        all_suggestions = []
        
        for criterion, score in criterion_scores.items():
            if not score.passed:
                all_issues.extend(score.issues)
                all_suggestions.extend(score.suggestions)
        
        # Add diagnostic issues
        for diag in diagnostics:
            if diag.severity in (DiagnosticSeverity.ERROR, DiagnosticSeverity.WARNING):
                all_issues.append(f"[{diag.source}] {diag.message}")
        
        review = ReviewResponse(
            status=status,
            goal_achieved=(status == ReviewStatus.APPROVED),
            confidence=overall_score / 100.0,
            issues=list(set(all_issues))[:10],  # Top 10 unique issues
            suggestions=list(set(all_suggestions))[:10],
            requirements_met=[
                c.value for c, s in criterion_scores.items() if s.passed
            ],
            requirements_failed=[
                c.value for c, s in criterion_scores.items() if not s.passed
            ],
        )
        
        self.logger.info(
            f"[REVIEWER] ✓ Review complete: "
            f"status={review.status.value}, "
            f"confidence={review.confidence:.2f}"
        )
        
        return review
    
    def _evaluate_criterion(
        self,
        criterion: ReviewCriterion,
        code: str,
        goal: str,
    ) -> CriterionScore:
        """Evaluate single criterion."""
        
        self.logger.debug(f"Evaluating criterion: {criterion.value}")
        
        prompt_template = self.REVIEW_PROMPTS[criterion]
        
        # For functional criterion, include goal
        if criterion == ReviewCriterion.FUNCTIONAL:
            prompt = prompt_template.format(requirement=goal, code=code[:1500])
        else:
            prompt = prompt_template.format(code=code[:1500])
        
        try:
            response = call_llm(prompt, return_json=False)
            result = extract_json(response)
            
            return CriterionScore(
                criterion=criterion,
                score=min(result.get("score", 0) / 100.0, 1.0),  # Normalize to 0-1
                passed=result.get("passed", False),
                issues=result.get("issues", []),
                suggestions=result.get("suggestions", []),
            )
        
        except Exception as e:
            self.logger.warning(f"Error evaluating {criterion.value}: {e}")
            # Fallback: conservative
            return CriterionScore(
                criterion=criterion,
                score=0.5,
                passed=False,
                issues=[str(e)],
                suggestions=[],
            )
    
    def get_detailed_report(
        self,
        goal: str,
        code: str,
    ) -> Dict:
        """Get detailed review report as dict."""
        
        review = self.review(goal, code)
        
        return {
            "goal": goal,
            "status": review.status.value,
            "confidence": review.confidence,
            "goal_achieved": review.goal_achieved,
            "issues": review.issues,
            "suggestions": review.suggestions,
            "requirements_met": review.requirements_met,
            "requirements_failed": review.requirements_failed,
        }
