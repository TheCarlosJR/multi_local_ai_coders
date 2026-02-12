"""
============================================================
AGENTE EXECUTOR (Execution Agent)
============================================================
Responsabilidade:
- Recebe steps do plano um a um
- Executa cada step chamando a ferramenta apropriada
- Retorna ExecutorResponse com histórico completo
- Em caso de erro, analisa com error_recovery_prompt

Fluxo:
  PlanStep → EXECUTOR_PROMPT + step → LLM → parse JSON
    ↓
  → Chamar tool (filesystem, terminal, git, web)
    ↓
  → Capturar output/erro
    ↓
  → ExecutorStepResponse ✓
"""

import json
import logging
from typing import List, Optional

from core.llm import call_llm, extract_json
from core.models import (
    PlanStep,
    ExecutorResponse,
    ExecutorStepResponse,
    ExecutionStatus,
    ToolCall,
    ToolType,
)
from core.config import logger
from prompts.executor_prompt import EXECUTOR_PROMPT
from prompts.error_recovery_prompt import ERROR_RECOVERY_PROMPT
from tools import filesystem_tool, terminal_tool, git_tool, web_tool
from agents.memory import MemoryAgent


class ExecutorAgent:
    """Agente responsável por executar steps do plano."""
    
    TOOL_MAP = {
        ToolType.FILESYSTEM: filesystem_tool,
        ToolType.TERMINAL: terminal_tool,
        ToolType.GIT: git_tool,
        ToolType.WEB: web_tool,
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.steps_executed: List[ExecutorStepResponse] = []
        self.memory = MemoryAgent()
    
    def execute(self, plan_steps: List[PlanStep]) -> ExecutorResponse:
        """
        Executa todos os steps do plano sequencialmente.
        
        Args:
            plan_steps: Lista de steps do plano a executar
        
        Returns:
            ExecutorResponse com histórico completo
        """
        
        self.logger.info(f"[EXECUTOR] Iniciando execução de {len(plan_steps)} steps")
        self.steps_executed = []
        
        for step in plan_steps:
            step_response = self._execute_step(step)
            self.steps_executed.append(step_response)
            
            if not step_response.success:
                self.logger.warning(
                    f"[EXECUTOR] Step {step.step_number} falhou. "
                    f"Parando execução."
                )
                break
        
        # Construir resposta final
        overall_success = all(s.success for s in self.steps_executed)
        final_result = "\n".join(
            f"Step {s.step_number}: {s.output_summary}" 
            for s in self.steps_executed
        )
        
        executor_response = ExecutorResponse(
            steps_completed=self.steps_executed,
            overall_success=overall_success,
            final_result=final_result,
            stopped_at_step=(
                self.steps_executed[-1].step_number 
                if not overall_success else None
            ),
            next_action=(
                "Retry with error recovery" if not overall_success else None
            ),
        )
        
        self.logger.info(
            f"[EXECUTOR] ✓ Execução concluída: "
            f"{len(self.steps_executed)} steps, "
            f"sucesso: {overall_success}"
        )
        
        return executor_response
    
    def _execute_step(self, step: PlanStep) -> ExecutorStepResponse:
        """Executa um step individual."""
        
        self.logger.info(f"[EXECUTOR] Executando step {step.step_number}: {step.description}")
        
        try:
            # Construir tool call a partir do step (não pedir ao LLM)
            tool_call = ToolCall(
                tool=step.tool,
                action=step.action,
                arguments={}  # LLM pode sugerir argumentos, mas por enquanto deixar vazio
            )
            
            # Executar tool
            result = self._call_tool(tool_call)
            
            step_response = ExecutorStepResponse(
                step_number=step.step_number,
                status=ExecutionStatus.SUCCESS,
                tool_call=tool_call,
                result=result[:500] if result else "",
                success=True,
                error_message=None,
                output_summary=(result[:100] if result else "Step completed")[:100],
            )
            
            self.logger.info(
                f"[EXECUTOR] ✓ Step {step.step_number} sucesso"
            )
            
            return step_response
            
        except Exception as e:
            self.logger.error(f"[EXECUTOR] Step {step.step_number} falhou: {e}")
            
            # Usar error recovery
            recovery = self._recover_from_error(step, str(e))
            
            step_response = ExecutorStepResponse(
                step_number=step.step_number,
                status=ExecutionStatus.FAILED,
                tool_call=ToolCall(
                    tool=ToolType.TERMINAL,
                    action="error",
                    arguments={"error": str(e)},
                ),
                result=str(e),
                success=False,
                error_message=str(e),
                output_summary=f"Erro: {str(e)[:80]}",
            )
            
            return step_response
    
    def _call_tool(self, tool_call: ToolCall) -> str:
        """Chama ferramenta apropriada com segurança."""
        
        tool_type = ToolType(tool_call.tool)
        action = tool_call.action
        args = tool_call.arguments
        
        if tool_type == ToolType.FILESYSTEM:
            if action == "read_file":
                return filesystem_tool.read_file(args.get("path", ""))
            elif action == "write_file":
                return filesystem_tool.write_file(
                    args.get("path", ""),
                    args.get("content", "")
                )
            elif action == "list_dir":
                return filesystem_tool.list_dir(args.get("path", "."))
                
        elif tool_type == ToolType.TERMINAL:
            if action == "run_command":
                return terminal_tool.run_cmd(args.get("command", ""))
                
        elif tool_type == ToolType.GIT:
            if action == "status":
                return git_tool.git_status()
            elif action == "commit":
                return git_tool.git_commit(args.get("message", ""))
            elif action == "diff":
                return git_tool.git_diff()
                
        elif tool_type == ToolType.WEB:
            if action == "fetch_url":
                return web_tool.fetch_url(args.get("url", ""))
                
        elif tool_type == ToolType.MEMORY:
            if action == "save_embedding":
                content = args.get("text", "")
                metadata = args.get("metadata", {})
                source = args.get("source", "execution")
                success = self.memory.save_memory(content, metadata, source)
                return f"Memory saved: {content[:100]}" if success else "Failed to save memory"
            elif action == "search_similar":
                query = args.get("query", "")
                top_k = args.get("top_k", 5)
                results = self.memory.recall_memory(query, top_k)
                return "\\n".join(f"{r.content} (score: {r.similarity_score})" for r in results) if results else "No similar memories found"
        
        raise ValueError(f"Ação desconhecida: {action}")
    
    def _recover_from_error(self, step: PlanStep, error: str) -> dict:
        """Analisa erro e sugere recuperação."""
        
        self.logger.info(f"[EXECUTOR] Analisando erro para recovery...")
        
        recovery_prompt = ERROR_RECOVERY_PROMPT.format(error_log=error)
        user_prompt = f"""
{recovery_prompt}

Original step: {step.description}
Error: {error}

Return JSON with root_cause, fix_strategy, next_step only.
"""
        
        try:
            response = call_llm(user_prompt, return_json=False)
            recovery = extract_json(response)
            return recovery
        except:
            return {
                "root_cause": error,
                "fix_strategy": "Retry",
                "next_step": step.description,
            }

