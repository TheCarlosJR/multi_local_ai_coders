"""
Testes de validação de schemas após mudanças críticas

Verifica:
- ExecutionContext.plan é opcional
- ErrorRecoveryResponse existe
- Pydantic v2 compatibility (.model_dump)
- Imports funcionam
"""

import pytest
from typing import List, Optional
from core.models import (
    ExecutionContext,
    PlanResponse,
    PlanStep,
    Risk,
    ErrorRecoveryResponse,
    ReviewResponse,
    ReviewIssue,
    ReviewStatus,
    ExecutorStepResponse,
    ExecutionStatus,
    ToolCall,
    ToolType,
)


class TestExecutionContextOptional:
    """Testa se plan é opcional em ExecutionContext."""
    
    def test_context_plan_is_optional(self):
        """ExecutionContext deve aceitar plan=None"""
        context = ExecutionContext(goal="Test goal", plan=None)
        assert context.goal == "Test goal"
        assert context.plan is None
    
    def test_context_plan_required_type(self):
        """ExecutionContext.plan deve ser Optional[PlanResponse]"""
        # Verificar que o campo plan no modelo é Optional
        assert ExecutionContext.model_fields['plan'].annotation == Optional[PlanResponse]
    
    def test_context_with_plan(self):
        """ExecutionContext pode receber um PlanResponse válido"""
        plan = PlanResponse(
            goal="Test",
            feasible=True,
            overall_strategy="Test strategy",
            steps=[
                PlanStep(
                    step_number=1,
                    description="Step 1",
                    tool=ToolType.FILESYSTEM,
                    action="read_file",
                    expected_output="File content",
                    dependencies=[]
                )
            ],
            risks=[],
            assumptions=[],
            estimated_duration_minutes=5
        )
        context = ExecutionContext(goal="Test goal", plan=plan)
        assert context.plan is not None
        assert context.plan.goal == "Test"


class TestErrorRecoveryResponse:
    """Testa o novo modelo ErrorRecoveryResponse."""
    
    def test_error_recovery_response_exists(self):
        """Verificar que ErrorRecoveryResponse foi criado"""
        recovery = ErrorRecoveryResponse(
            root_cause="Test error",
            fix_strategy="Try again",
            next_step="Retry step 1"
        )
        assert recovery.root_cause == "Test error"
        assert recovery.fix_strategy == "Try again"
        assert recovery.next_step == "Retry step 1"
    
    def test_error_recovery_model_dump(self):
        """Verificar .model_dump() funciona (Pydantic v2)"""
        recovery = ErrorRecoveryResponse(
            root_cause="Error",
            fix_strategy="Fix",
            next_step="Next"
        )
        dump = recovery.model_dump()
        assert isinstance(dump, dict)
        assert dump['root_cause'] == "Error"


class TestReviewerSchemaUpdate:
    """Testa mudanças no schema do Reviewer."""
    
    def test_review_response_fields(self):
        """ReviewResponse deve ter campos esperados"""
        # Verificar que ReviewIssue não tem 'type' field
        issue = ReviewIssue(
            issue="Test issue",
            severity="high",
            suggestion="Fix it"
        )
        dump = issue.model_dump()
        assert 'issue' in dump
        assert 'severity' in dump
        assert 'suggestion' in dump
        # 'type' não deve estar mais no modelo
    
    def test_review_status_enum_values(self):
        """ReviewStatus deve ter valores esperados"""
        assert ReviewStatus.APPROVED == "approved"
        assert ReviewStatus.NEEDS_REFINEMENT == "needs_refinement"
        assert ReviewStatus.FAILED == "failed"


class TestPlanResponseSchema:
    """Testa se PlanResponse foi atualizado corretamente."""
    
    def test_plan_response_feasible_required(self):
        """PlanResponse deve ter campo 'feasible' obrigatório"""
        plan = PlanResponse(
            goal="Test goal",
            feasible=True,
            overall_strategy="Strategy",
            steps=[],
            risks=[],
            assumptions=[],
            estimated_duration_minutes=10
        )
        assert plan.feasible is True
    
    def test_plan_step_has_required_fields(self):
        """PlanStep deve ter todos os campos necessários"""
        step = PlanStep(
            step_number=1,
            description="Do something",
            tool=ToolType.TERMINAL,
            action="run_command",
            expected_output="Success",
            dependencies=[]
        )
        assert step.step_number == 1
        assert step.tool == ToolType.TERMINAL
        assert step.action == "run_command"
    
    def test_risk_object_has_fields(self):
        """Risk deve ser objeto com severity e mitigation"""
        risk = Risk(
            risk="Could fail",
            severity="high",
            mitigation="Add check"
        )
        assert risk.risk == "Could fail"
        assert risk.severity == "high"
        assert risk.mitigation == "Add check"
    
    def test_plan_response_dependencies_field(self):
        """PlanStep deve suportar dependencies"""
        step = PlanStep(
            step_number=2,
            description="Step 2",
            tool=ToolType.GIT,
            action="commit",
            expected_output="Committed",
            dependencies=[1]  # Depende do step 1
        )
        assert step.dependencies == [1]


class TestToolTypeMemory:
    """Testa se ToolType.MEMORY está disponível."""
    
    def test_tool_type_memory_exists(self):
        """ToolType.MEMORY deve existir"""
        assert ToolType.MEMORY == "memory"
    
    def test_tool_type_all_values(self):
        """Verificar que todos os tool types esperados existem"""
        assert ToolType.FILESYSTEM == "filesystem"
        assert ToolType.TERMINAL == "terminal"
        assert ToolType.GIT == "git"
        assert ToolType.WEB == "web"
        assert ToolType.MEMORY == "memory"


class TestModelDumpMethod:
    """Testa se .model_dump() funciona em todos os modelos (Pydantic v2)."""
    
    def test_execution_context_model_dump(self):
        """ExecutionContext.model_dump() deve funcionar"""
        context = ExecutionContext(goal="Test", plan=None)
        dump = context.model_dump()
        assert isinstance(dump, dict)
        assert dump['goal'] == "Test"
        assert dump['plan'] is None
    
    def test_executor_step_response_model_dump(self):
        """ExecutorStepResponse.model_dump() deve funcionar"""
        step = ExecutorStepResponse(
            step_number=1,
            status=ExecutionStatus.SUCCESS,
            tool_call=ToolCall(
                tool=ToolType.FILESYSTEM,
                action="read_file",
                arguments={}
            ),
            result="Success",
            success=True,
            error_message=None,
            output_summary="Done"
        )
        dump = step.model_dump()
        assert isinstance(dump, dict)
        assert dump['success'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
