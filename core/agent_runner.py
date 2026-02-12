"""
============================================================
AGENT RUNNER - Orquestrador Principal
============================================================
Responsabilidade:
- Coordenar Planner → Executor → Reviewer
- Integrar memory retrieval (RAG)
- Implementar retry logic
- Refinement loop se necessário
- Persistência de aprendizados

Fluxo Completo:
  1. Memory.recall_memory(goal) → contexto
  2. Planner.plan(goal, contexto) → PlanResponse
  3. Executor.execute(steps) → ExecutorResponse
  4. Reviewer.review(resultado) → ReviewResponse
  5. Se APPROVED → salvar memoria → FIM
  6. Se NEEDS_REFINEMENT → retry com feedback
  7. Se FAILED → tentativa 2 com error recovery
"""

import logging
from typing import Optional, Dict, Any

from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.reviewer import ReviewerAgent
from agents.memory import MemoryAgent
from core.models import (
    PlanResponse,
    ExecutorResponse,
    ReviewResponse,
    ReviewStatus,
    ExecutionContext,
)
from core.config import (
    MAX_RETRIES,
    ENABLE_REFINEMENT_LOOP,
    ENABLE_MEMORY_RETRIEVAL,
    AUTO_COMMIT,
    logger,
)
from core.llm import call_llm
from prompts.commit_message_prompt import COMMIT_PROMPT
from tools import git_tool

log = logging.getLogger(__name__)


class AgentRunner:
    """Orquestrador dos agentes IA autônomos."""
    
    def __init__(self):
        """Inicializa todos os agentes."""
        
        self.planner = PlannerAgent()
        self.executor = ExecutorAgent()
        self.reviewer = ReviewerAgent()
        self.memory = MemoryAgent()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("✓ AgentRunner inicializado")
    
    def run(self, goal: str) -> Dict[str, Any]:
        """
        Executa o fluxo completo do agente autônomo.
        
        Args:
            goal: Objetivo a alcançar
        
        Returns:
            Dicionário com resultado final e histórico
        """
        
        self.logger.info("=" * 60)
        self.logger.info(f"[GOAL] {goal}")
        self.logger.info("=" * 60)
        
        # Inicializar contexto de execução
        context = ExecutionContext(goal=goal, plan=None)
        
        for attempt in range(MAX_RETRIES):
            self.logger.info(f"\n[ATTEMPT {attempt + 1}/{MAX_RETRIES}]")
            
            try:
                # ============================================================
                # PHASE 1: MEMORY RETRIEVAL
                # ============================================================
                
                memory_context = ""
                if ENABLE_MEMORY_RETRIEVAL:
                    self.logger.info("\n[PHASE 1] Memory Retrieval...")
                    memory_context = self.memory.get_context(goal)
                    if memory_context:
                        self.logger.info(f"✓ Contexto recuperado da memória")
                        context.retrieved_memories = self.memory.recall_memory(goal)
                
                # ============================================================
                # PHASE 2: PLANNING
                # ============================================================
                
                self.logger.info("\n[PHASE 2] Planning...")
                plan = self.planner.plan(goal, memory_context=memory_context)
                context.plan = plan
                
                if not plan.feasible:
                    self.logger.error(f"✗ Objetivo não é viável: {plan.overall_strategy}")
                    return {
                        "success": False,
                        "error": f"Objetivo não viável: {plan.overall_strategy}",
                        "context": context.model_dump(),
                    }
                
                self.logger.info(
                    f"✓ Plano criado: {len(plan.steps)} steps, "
                    f"tempo estimado: {plan.estimated_duration_minutes}min"
                )
                
                # ============================================================
                # PHASE 3: EXECUTION
                # ============================================================
                
                self.logger.info("\n[PHASE 3] Execution...")
                execution_result = self.executor.execute(plan.steps)
                context.execution_history = execution_result.steps_completed
                
                if not execution_result.overall_success:
                    self.logger.warning(
                        f"✗ Execução falhou no step "
                        f"{execution_result.stopped_at_step}"
                    )
                
                # ============================================================
                # PHASE 4: REVIEW
                # ============================================================
                
                self.logger.info("\n[PHASE 4] Review...")
                review = self.reviewer.review(
                    goal=goal,
                    execution_result=execution_result.final_result,
                    plan_description=plan.overall_strategy,
                )
                
                self.logger.info(
                    f"Review: status={review.status.value}, "
                    f"confidence={review.confidence:.2%}, "
                    f"issues={len(review.issues)}"
                )
                
                # ============================================================
                # PHASE 5: DECISION
                # ============================================================
                
                if review.status == ReviewStatus.APPROVED:
                    # ✓ SUCESSO
                    self.logger.info("\n" + "=" * 60)
                    self.logger.info("✓ OBJETIVO ALCANÇADO!")
                    self.logger.info("=" * 60)
                    
                    # Salvar na memória
                    self._save_success_to_memory(goal, execution_result, review)
                    
                    # Auto-commit se configurado
                    if AUTO_COMMIT:
                        self._attempt_auto_commit(goal)
                    
                    return {
                        "success": True,
                        "goal": goal,
                        "result": execution_result.final_result,
                        "review": review.model_dump(),
                        "context": context.model_dump(),
                    }
                
                elif review.status == ReviewStatus.NEEDS_REFINEMENT:
                    # Tentar refinar se ativado
                    if ENABLE_REFINEMENT_LOOP and attempt < MAX_RETRIES - 1:
                        self.logger.info(
                            f"\n[REFINEMENT] {review.recommendation}\n"
                        )
                        context.iteration_count += 1
                        continue  # Proxima iteração
                    else:
                        # Atingiu limite de retries
                        return {
                            "success": False,
                            "error": f"Refinamento não resolveu: {review.recommendation}",
                            "review": review.model_dump(),
                            "context": context.model_dump(),
                        }
                
                else:  # FAILED
                    # Tentar recuperação
                    if attempt < MAX_RETRIES - 1:
                        self.logger.warning(
                            f"Tentando recuperação (erro: {review.issues})"
                        )
                        context.iteration_count += 1
                        context.errors_recovered += 1
                        continue
                    else:
                        return {
                            "success": False,
                            "error": f"Falha não recuperável: {review.recommendation}",
                            "issues": [i.model_dump() for i in review.issues],
                            "context": context.model_dump(),
                        }
                        
            except Exception as e:
                self.logger.error(f"✗ Erro na execução: {e}", exc_info=True)
                
                if attempt < MAX_RETRIES - 1:
                    self.logger.info(f"Retentando...")
                    continue
                else:
                    return {
                        "success": False,
                        "error": str(e),
                        "context": context.model_dump(),
                    }
        
        return {
            "success": False,
            "error": f"Limite de tentativas ({MAX_RETRIES}) excedido",
            "context": context.model_dump(),
        }
    
    def _save_success_to_memory(
        self,
        goal: str,
        execution: ExecutorResponse,
        review: ReviewResponse,
    ) -> None:
        """Salva execução bem-sucedida na memória para aprendizado futuro."""
        
        try:
            memory_text = f"""
SUCCESSFUL EXECUTION:
Goal: {goal}
Result: {execution.final_result}
Steps: {len(execution.steps_completed)}
Confidence: {review.confidence:.2%}
"""
            
            self.memory.save_memory(
                content=memory_text.strip(),
                metadata={"status": "success", "confidence": str(review.confidence)},
                source=f"successful_goal_{goal[:20]}",
            )
            
            self.logger.info("✓ Sucesso salvo na memória")
            
        except Exception as e:
            self.logger.warning(f"Não conseguiu salvar na memória: {e}")
    
    def _attempt_auto_commit(self, goal: str) -> None:
        """Faz auto-commit das mudanças com mensagem gerada via LLM."""
        
        try:
            status = git_tool.git_status()
            
            if "nothing to commit" in status.lower() or "clean" in status.lower():
                self.logger.info("(Nenhuma mudança para commitar)")
                return
            
            # Extrair diff para contexto
            try:
                diff = git_tool.git_diff()
            except:
                diff = "(diff não disponível)"
            
            # Gerar mensagem via LLM
            try:
                prompt = COMMIT_PROMPT.format(goal=goal, changes=diff[:500])
                commit_msg = call_llm(
                    user_prompt=prompt,
                    return_json=False,
                ).strip()
                
                # Limitar tamanho
                if len(commit_msg) > 100:
                    commit_msg = commit_msg[:100]
                    
                git_tool.git_commit(commit_msg)
                self.logger.info(f"✓ Auto-commit: {commit_msg}")
                
            except Exception as llm_error:
                # Fallback para mensagem simples se LLM falhar
                self.logger.warning(f"LLM commit falhou, usando fallback: {llm_error}")
                commit_msg = f"Auto: {goal[:50]}"
                git_tool.git_commit(commit_msg)
                self.logger.info(f"✓ Auto-commit (fallback): {commit_msg}")
            
        except Exception as e:
            self.logger.warning(f"Auto-commit falhou: {e}")


# ============================================================
# INTERFACE PÚBLICA
# ============================================================

_runner = None


def run(goal: str) -> Dict[str, Any]:
    """
    Interface pública: executa o agente para um objetivo.
    
    Uso:
        from core.agent_runner import run
        result = run("Crie um arquivo hello.py")
        print(result)
    
    Args:
        goal: Objetivo em natural language
    
    Returns:
        Dicionário com resultado, histórico e metadados
    """
    
    global _runner
    if not _runner:
        _runner = AgentRunner()
    
    return _runner.run(goal)

