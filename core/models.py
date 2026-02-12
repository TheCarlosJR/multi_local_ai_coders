"""
============================================================
MODELOS DE DADOS ESTRUTURADOS (Pydantic)
============================================================
Definição de schemas JSON para output dos agentes.
Valida e estrutura as respostas do LLM.

Fluxo:
  Planner → PlanResponse (steps, risks, time)
    ↓
  Executor → ExecutorStepResponse (action, result, success)
    ↓
  Reviewer → ReviewResponse (status, issues, recommendation)
============================================================
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================
# ENUMS (Tipos controlados)
# ============================================================

class ToolType(str, Enum):
    """Tipos de ferramentas disponíveis."""
    FILESYSTEM = "filesystem"  # read_file, write_file, list_dir
    TERMINAL = "terminal"      # run_command
    GIT = "git"                # commit, push, pull, status
    WEB = "web"                # fetch_url, scrape
    MEMORY = "memory"          # save_embedding, search_similar


class ExecutionStatus(str, Enum):
    """Status de execução de um step."""
    PENDING = "pending"        # Ainda não executado
    IN_PROGRESS = "in_progress"  # Executando
    SUCCESS = "success"        # Sucesso
    FAILED = "failed"          # Falha
    SKIPPED = "skipped"        # Pulado


class ReviewStatus(str, Enum):
    """Status final da revisão."""
    APPROVED = "approved"      # Objetivo alcançado
    NEEDS_REFINEMENT = "needs_refinement"  # Requer ajustes
    FAILED = "failed"          # Objetivo não alcançado


# ============================================================
# PLANNER OUTPUT
# ============================================================

class PlanStep(BaseModel):
    """Um step individual do plano."""
    
    step_number: int = Field(..., description="Ordem de execução (1, 2, 3...)")
    description: str = Field(..., description="O que fazer")
    tool: ToolType = Field(..., description="Qual ferramenta usar")
    action: str = Field(..., description="Ação específica na ferramenta")
    expected_output: str = Field(..., description="O que espera como resultado")
    dependencies: List[int] = Field(
        default_factory=list,
        description="Steps anteriores necessários"
    )


class Risk(BaseModel):
    """Um risco potencial."""
    
    risk: str = Field(..., description="Descrição do risco")
    severity: str = Field(..., description="low, medium, high")
    mitigation: str = Field(..., description="Como mitigar")


class PlanResponse(BaseModel):
    """Resposta estruturada do Planner."""
    
    goal: str = Field(..., description="Objetivo original")
    feasible: bool = Field(..., description="É possível executar?")
    overall_strategy: str = Field(
        ...,
        description="Estratégia geral em 1-2 linhas"
    )
    steps: List[PlanStep] = Field(..., description="Steps a executar")
    risks: List[Risk] = Field(default_factory=list, description="Riscos")
    assumptions: List[str] = Field(
        default_factory=list,
        description="Suposições (ex: git repo existe, arquivo X está presente)"
    )
    estimated_duration_minutes: int = Field(
        default=5,
        description="Tempo estimado"
    )


# ============================================================
# EXECUTOR OUTPUT
# ============================================================

class ToolCall(BaseModel):
    """Chamada a uma ferramenta específica."""
    
    tool: ToolType = Field(..., description="Qual ferramenta")
    action: str = Field(..., description="Ação (ex: 'read_file', 'run_command')")
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Argumentos da ação (ex: {'path': '/file.txt'})"
    )


class ExecutorStepResponse(BaseModel):
    """Resposta estruturada de um step executado."""
    
    step_number: int = Field(..., description="Qual step foi executado")
    status: ExecutionStatus = Field(..., description="Resultado")
    tool_call: ToolCall = Field(..., description="Ferramenta chamada")
    result: str = Field(..., description="Output da ferramenta ou erro")
    success: bool = Field(..., description="Correu bem?")
    error_message: Optional[str] = Field(
        default=None,
        description="Mensagem de erro se falhou"
    )
    output_summary: str = Field(
        ...,
        description="Resumo do resultado em 1-2 linhas"
    )


class ExecutorResponse(BaseModel):
    """Resposta estruturada do Executor (multiplos steps)."""
    
    steps_completed: List[ExecutorStepResponse] = Field(
        ...,
        description="Histórico de execução"
    )
    overall_success: bool = Field(..., description="Tudo correu bem?")
    final_result: str = Field(..., description="Resultado final")
    stopped_at_step: Optional[int] = Field(
        default=None,
        description="Se parou, em qual step?"
    )
    next_action: Optional[str] = Field(
        default=None,
        description="Próxima ação sugerida se falhou"
    )


# ============================================================
# REVIEWER OUTPUT
# ============================================================

class ReviewIssue(BaseModel):
    """Um problema encontrado na revisão."""
    
    issue: str = Field(..., description="Descrição do problema")
    severity: str = Field(..., description="low, medium, high")
    suggestion: str = Field(..., description="Como corrigir")


class ReviewResponse(BaseModel):
    """Resposta estruturada do Reviewer."""
    
    goal_achieved: bool = Field(..., description="Objetivo foi alcançado?")
    status: ReviewStatus = Field(..., description="APPROVED, NEEDS_REFINEMENT, FAILED")
    summary: str = Field(..., description="Resumo da avaliação")
    issues: List[ReviewIssue] = Field(
        default_factory=list,
        description="Problemas encontrados"
    )
    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="Confiança na avaliação (0.0-1.0)"
    )
    recommendation: str = Field(
        ...,
        description="Recomendação: finalizar, refinar plano, tentar outra abordagem?"
    )


# ============================================================
# MEMORY / RAG
# ============================================================

class MemoryEntry(BaseModel):
    """Um entry de memória armazenado."""
    
    content: str = Field(..., description="Texto a embutir")
    metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Tags (ex: {'task': 'git', 'status': 'success'})"
    )
    source: str = Field(
        ...,
        description="De onde veio (ex: 'plan_review_1', 'error_recovery')"
    )


class MemorySearchResult(BaseModel):
    """Resultado de busca de memória similar."""
    
    content: str = Field(..., description="Conteúdo encontrado")
    similarity_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Quão similar é (0.0-1.0)"
    )
    source: str = Field(..., description="De onde é")


# ============================================================
# CONTEXTO DE EXECUÇÃO (Estado)
# ============================================================

class ErrorRecoveryResponse(BaseModel):
    """Resposta estruturada de recuperação de erro."""
    
    root_cause: str = Field(..., description="Causa raiz do erro")
    fix_strategy: str = Field(..., description="Estratégia para corrigir")
    next_step: str = Field(..., description="Próximo passo recomendado")


class ExecutionContext(BaseModel):
    """Estado da execução atual."""
    
    goal: str = Field(..., description="Objetivo original")
    plan: Optional[PlanResponse] = Field(default=None, description="Plano atual")
    execution_history: List[ExecutorStepResponse] = Field(
        default_factory=list,
        description="O que foi executado"
    )
    retrieved_memories: List[MemorySearchResult] = Field(
        default_factory=list,
        description="Memórias relevantes encontradas"
    )
    iteration_count: int = Field(default=1, description="Iteração atual")
    errors_recovered: int = Field(default=0, description="Erros recuperados")
    
    def last_step_succeeded(self) -> bool:
        """Último step teve sucesso?"""
        if not self.execution_history:
            return False
        return self.execution_history[-1].success
