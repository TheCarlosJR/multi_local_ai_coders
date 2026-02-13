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


# ============================================================
# TEST EXECUTION
# ============================================================

class TestResult(BaseModel):
    """Um teste individual executado."""
    
    test_name: str = Field(..., description="Nome do teste")
    passed: bool = Field(..., description="Passou?")
    duration: float = Field(default=0.0, description="Tempo em segundos")
    file: str = Field(..., description="Arquivo do teste")
    error_message: Optional[str] = Field(
        default=None,
        description="Mensagem de erro se falhou"
    )


class TestSuiteResult(BaseModel):
    """Resultado de uma suite de testes."""
    
    suite_name: str = Field(..., description="Nome da suite (ex: test_main.py)")
    total_tests: int = Field(..., description="Total de testes")
    passed: int = Field(..., description="Testes que passaram")
    failed: int = Field(..., description="Testes que falharam")
    skipped: int = Field(default=0, description="Testes pulados")
    coverage: Optional[float] = Field(
        default=None,
        description="Cobertura de código (%)"
    )
    duration: float = Field(default=0.0, description="Tempo total em segundos")
    failed_tests: List[TestResult] = Field(
        default_factory=list,
        description="Detalhes dos testes que falharam"
    )


class TestExecutionResult(BaseModel):
    """Resultado completo de execução de testes."""
    
    success: bool = Field(..., description="Todos os testes passaram?")
    total_suites: int = Field(..., description="Número de suites")
    total_tests: int = Field(..., description="Número total de testes")
    total_passed: int = Field(..., description="Total de testes que passaram")
    total_failed: int = Field(..., description="Total de testes que falharam")
    overall_coverage: Optional[float] = Field(
        default=None,
        description="Cobertura geral (%)"
    )
    suites: List[TestSuiteResult] = Field(
        default_factory=list,
        description="Resultados por suite"
    )


# ============================================================
# TYPE CHECKING
# ============================================================

class TypeCheckIssue(BaseModel):
    """Um problema de tipo detectado."""
    
    file: str = Field(..., description="Arquivo")
    line: int = Field(..., description="Número da linha")
    column: int = Field(default=0, description="Coluna")
    message: str = Field(..., description="Mensagem de erro")
    severity: str = Field(..., description="error, warning, info")
    code: Optional[str] = Field(default=None, description="Código do erro (ex: E302)")


class TypeCheckResult(BaseModel):
    """Resultado de validação de tipos."""
    
    file: str = Field(..., description="Arquivo analisado")
    language: str = Field(..., description="Linguagem (py, ts, js)")
    success: bool = Field(..., description="Sem erros de tipo?")
    total_issues: int = Field(..., description="Número de problemas")
    issues: List[TypeCheckIssue] = Field(
        default_factory=list,
        description="Detalhes dos problemas"
    )


# ============================================================
# STATIC ANALYSIS
# ============================================================

class AnalysisIssue(BaseModel):
    """Um problema de análise estática."""
    
    file: str = Field(..., description="Arquivo")
    line: int = Field(..., description="Número da linha")
    column: int = Field(default=0, description="Coluna")
    message: str = Field(..., description="Mensagem do problema")
    code: str = Field(..., description="Código do problema (ex: E501)")
    severity: str = Field(..., description="error, warning, info")
    tool: str = Field(default="pylint", description="Ferramenta que detectou")


class AnalysisResult(BaseModel):
    """Resultado de análise estática de código."""
    
    file: str = Field(..., description="Arquivo analisado")
    language: str = Field(..., description="Linguagem")
    total_violations: int = Field(..., description="Número de violações")
    violations: List[AnalysisIssue] = Field(
        default_factory=list,
        description="Detalhes das violações"
    )
    complexity_score: Optional[float] = Field(
        default=None,
        description="Complexidade ciclomática (0-100)"
    )


# ============================================================
# CODE CACHING
# ============================================================

class CodeSnippet(BaseModel):
    """Um snippet de código no cache."""
    
    language: str = Field(..., description="Linguagem (py, ts, js, etc)")
    code: str = Field(..., description="Código")
    description: str = Field(default="", description="O que faz")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tags (ex: {'tag': 'validation', 'task': 'email'})"
    )
    usage_count: int = Field(default=0, description="Quantas vezes foi usado")
    success_rate: float = Field(
        default=1.0,
        ge=0,
        le=1,
        description="Taxa de sucesso (0.0-1.0)"
    )
    created_at: str = Field(..., description="Data de criação")
    contexts: List[str] = Field(
        default_factory=list,
        description="Contextos onde foi usado com sucesso"
    )


class CacheEntry(BaseModel):
    """Um entry de cache de code snippets."""
    
    snippet_id: str = Field(..., description="ID único do snippet")
    snippet: CodeSnippet = Field(..., description="Código")
    last_used: str = Field(..., description="Última vez usado")
    similarity_score: Optional[float] = Field(
        default=None,
        description="Score de similaridade com query (0-1)"
    )


# ============================================================
# CI/CD & QUALITY GATES
# ============================================================

class QualityGateResult(BaseModel):
    """Resultado de um quality gate."""
    
    gate_name: str = Field(..., description="Nome do gate")
    passed: bool = Field(..., description="Passou?")
    message: str = Field(..., description="Detalhes")
    severity: str = Field(..., description="error, warning, info")


class PreExecutionValidation(BaseModel):
    """Resultado da validação pré-execução (CI/CD gate)."""
    
    success: bool = Field(..., description="Tudo passou?")
    type_check: Optional[TypeCheckResult] = Field(
        default=None,
        description="Resultado de type checking"
    )
    static_analysis: Optional[AnalysisResult] = Field(
        default=None,
        description="Resultado de análise estática"
    )
    test_results: Optional[TestExecutionResult] = Field(
        default=None,
        description="Resultado de execução de testes"
    )
    quality_gates: List[QualityGateResult] = Field(
        default_factory=list,
        description="Resultado de quality gates customizados"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Warnings (não bloqueiam execução)"
    )


# ============================================================
# PHASE 8: ERROR PATTERN LEARNING
# ============================================================

class ErrorSolution(BaseModel):
    """Solução registrada para um padrão de erro."""
    
    description: str = Field(..., description="Descrição da solução")
    fix_type: str = Field(..., description="Tipo: import_fix, type_annotation, refactor, error_handling, manual")
    code_fix: Optional[str] = Field(default="", description="Código da correção")
    success_rate: float = Field(
        default=0.0,
        description="Taxa de sucesso (0-1)"
    )
    attempts: int = Field(default=0, description="Número de tentativas")


class ErrorPattern(BaseModel):
    """Padrão de erro detectado e armazenado."""
    
    signature: str = Field(..., description="Assinatura do erro (ex: TypeError:type_mismatch)")
    error_type: str = Field(..., description="Tipo de erro (ex: TypeError)")
    language: str = Field(..., description="Linguagem (python, javascript, etc)")
    frequency: int = Field(default=0, description="Quantas vezes foi visto")
    solutions: List[ErrorSolution] = Field(
        default_factory=list,
        description="Soluções tentadas para este padrão"
    )
    first_seen: str = Field(..., description="ISO timestamp primeira ocorrência")
    timestamp: Optional[str] = Field(default=None, description="ISO timestamp última ocorrência")


class PatternAnalysis(BaseModel):
    """Análise de um erro contra padrões conhecidos."""
    
    error_signature: str = Field(..., description="Assinatura do erro")
    error_type: str = Field(..., description="Tipo de erro")
    language: str = Field(..., description="Linguagem")
    code_context: str = Field(default="", description="Contexto de código")
    matched_patterns: List[ErrorPattern] = Field(
        default_factory=list,
        description="Padrões similares encontrados"
    )
    suggested_solutions: List[ErrorSolution] = Field(
        default_factory=list,
        description="Soluções sugeridas"
    )
    pattern_frequency: int = Field(default=0, description="Quantas vezes foi visto")
    success_rate: float = Field(default=0.0, description="Taxa de sucesso (0-1)")
    timestamp: str = Field(..., description="ISO timestamp da análise")
