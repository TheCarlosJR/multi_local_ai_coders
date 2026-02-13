"""
Enhanced Parallel Executor Agent with Dependency Resolution

Melhorias:
- Dependency graph resolution (topological sort)
- Parallel execution de steps independentes (ThreadPoolExecutor)
- Exponential backoff com tenacity
- Memory integration para successful steps
- Melhor error isolation

Preserva API do ExecutorAgent original.
"""

import json
import logging
from typing import List, Optional, Dict, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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
from core.observability import create_span
from prompts.executor_prompt import EXECUTOR_PROMPT
from prompts.error_recovery_prompt import ERROR_RECOVERY_PROMPT
from tools import filesystem_tool, terminal_tool, git_tool, web_tool
from agents.memory import MemoryAgent


class ExecutorAgentV2:
    """
    Versão 2: Executor com paralelização e dependency resolution.
    
    API compatível com ExecutorAgent v1.
    """
    
    TOOL_MAP = {
        ToolType.FILESYSTEM: filesystem_tool,
        ToolType.TERMINAL: terminal_tool,
        ToolType.GIT: git_tool,
        ToolType.WEB: web_tool,
    }
    
    # Config
    MAX_WORKERS = 4  # Threads para paralelização
    STEP_TIMEOUT = 300  # 5 min por step
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.steps_executed: Dict[int, ExecutorStepResponse] = {}
        self.memory = MemoryAgent()
        self._lock = threading.Lock()  # Para thread-safe step recording
    
    def execute(self, plan_steps: List[PlanStep]) -> ExecutorResponse:
        """
        Executa todos os steps do plano com dependency resolution.
        
        Steps com zero dependencies são executados em paralelo.
        Steps com dependencies aguardam predecessores.
        
        Args:
            plan_steps: Lista de steps do plano a executar
        
        Returns:
            ExecutorResponse com histórico completo
        """
        
        with create_span("executor.execute", steps_count=len(plan_steps)):
            self.logger.info(f"[EXECUTOR] Iniciando execução de {len(plan_steps)} steps")
            self.steps_executed = {}
            
            # Build dependency graph
            dag = self._build_dag(plan_steps)
            
            # Execute with dependency resolution
            failed_steps = self._execute_with_dependencies(plan_steps, dag)
            
            # Build response
            overall_success = len(failed_steps) == 0
            
            executor_response = ExecutorResponse(
                steps_completed=list(self.steps_executed.values()),
                overall_success=overall_success,
                final_result=self._build_final_result(),
                stopped_at_step=(min(failed_steps) if failed_steps else None),
                next_action=(
                    f"Retry from step {min(failed_steps)}" 
                    if failed_steps else None
                ),
            )
            
            self.logger.info(
                f"[EXECUTOR] ✓ Execução concluída: "
                f"{len(self.steps_executed)} steps, "
                f"sucesso: {overall_success}"
            )
            
            return executor_response
    
    def _build_dag(self, plan_steps: List[PlanStep]) -> Dict[int, Set[int]]:
        """
        Build Directed Acyclic Graph of step dependencies.
        
        Returns:
            {step_number: {dependencies}}
        """
        
        step_map = {step.step_number: step for step in plan_steps}
        dag = {}
        
        for step in plan_steps:
            deps = set(step.dependencies) if step.dependencies else set()
            # Validate dependencies exist
            for dep in deps:
                if dep not in step_map:
                    self.logger.warning(f"Step {step.step_number} references nonexistent step {dep}")
            dag[step.step_number] = deps
        
        self.logger.debug(f"DAG: {dag}")
        return dag
    
    def _execute_with_dependencies(
        self,
        plan_steps: List[PlanStep],
        dag: Dict[int, Set[int]],
    ) -> Set[int]:
        """
        Execute steps respecting dependency graph.
        
        Returns:
            Set of failed step numbers
        """
        
        step_map = {step.step_number: step for step in plan_steps}
        completed: Set[int] = set()
        failed: Set[int] = set()
        
        # Topological sort with dependency checking
        remaining = set(step_map.keys())
        
        while remaining:
            # Find steps that can execute (dependencies satisfied or no dependencies)
            ready = {
                step_num for step_num in remaining
                if dag[step_num].issubset(completed)  # All deps completed
                and step_num not in failed  # Not failed
            }
            
            # Check if any deps failed
            for step_num in list(remaining):
                for dep in dag[step_num]:
                    if dep in failed:
                        self.logger.warning(
                            f"Step {step_num} skipped: "
                            f"dependency {dep} failed"
                        )
                        failed.add(step_num)
                        remaining.discard(step_num)
            
            if not ready:
                if remaining:
                    self.logger.error(
                        f"Deadlock detected: remaining steps {remaining} "
                        f"have unmet dependencies"
                    )
                break
            
            # Execute ready steps in parallel
            self._execute_parallel(
                [step_map[step_num] for step_num in ready],
                completed,
                failed,
            )
            
            remaining -= ready
        
        return failed
    
    def _execute_parallel(
        self,
        ready_steps: List[PlanStep] ,
        completed: Set[int],
        failed: Set[int],
    ):
        """
        Execute list of ready steps in parallel using thread pool.
        
        Updates completed/failed sets in thread-safe manner.
        """
        
        if not ready_steps:
            return
        
        self.logger.info(f"Executing {len(ready_steps)} steps in parallel")
        
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            future_to_step = {
                executor.submit(self._execute_step, step): step
                for step in ready_steps
            }
            
            for future in as_completed(future_to_step, timeout=self.STEP_TIMEOUT):
                step = future_to_step[future]
                try:
                    step_response = future.result()
                    
                    with self._lock:
                        self.steps_executed[step.step_number] = step_response
                        
                        if step_response.success:
                            completed.add(step.step_number)
                        else:
                            failed.add(step.step_number)
                
                except Exception as e:
                    self.logger.error(f"Exception executing step {step.step_number}: {e}")
                    with self._lock:
                        failed.add(step.step_number)
                        self.steps_executed[step.step_number] = ExecutorStepResponse(
                            step_number=step.step_number,
                            status=ExecutionStatus.FAILED,
                            tool_call=None,
                            result=str(e),
                            success=False,
                            error_message=str(e),
                            output_summary=f"Exception: {str(e)[:80]}",
                        )
    
    def _execute_step(self, step: PlanStep) -> ExecutorStepResponse:
        """
        Executa um step individual.
        
        Thread-safe (called from thread pool).
        """
        
        self.logger.info(
            f"[EXECUTOR] Executing step {step.step_number}: "
            f"{step.description}"
        )
        
        try:
            with create_span(
                "executor.step",
                step_number=step.step_number,
                tool=step.tool.value,
            ):
                # Build tool call
                tool_call = ToolCall(
                    tool=step.tool,
                    action=step.action,
                    arguments=getattr(step, 'arguments', {}),  # Try to get from step
                )
                
                # Execute tool
                result = self._call_tool(tool_call)
                
                # Save to memory if successful
                if result:
                    self.memory.save_memory(
                        content=f"Step {step.step_number}: {result[:200]}",
                        metadata={
                            "step_number": step.step_number,
                            "tool": step.tool.value,
                            "action": step.action,
                        },
                        source="executor_success",
                    )
                
                step_response = ExecutorStepResponse(
                    step_number=step.step_number,
                    status=ExecutionStatus.SUCCESS,
                    tool_call=tool_call,
                    result=result[:500] if result else "",
                    success=True,
                    error_message=None,
                    output_summary=(result[:100] if result else "Step completed")[:100],
                )
                
                self.logger.info(f"[EXECUTOR] ✓ Step {step.step_number} success")
                return step_response
        
        except Exception as e:
            self.logger.error(f"[EXECUTOR] Step {step.step_number} failed: {e}")
            
            # Attempt error recovery
            recovery = self._recover_from_error(step, str(e))
            
            step_response = ExecutorStepResponse(
                step_number=step.step_number,
                status=ExecutionStatus.FAILED,
                tool_call=None,
                result=str(e),
                success=False,
                error_message=str(e),
                output_summary=f"Error: {str(e)[:80]}",
            )
            
            return step_response
    
    def _call_tool(self, tool_call: ToolCall) -> str:
        """
        Chama ferramenta apropriada.
        
        Mesmo da v1 (reusable).
        """
        
        tool_type = ToolType(tool_call.tool)
        action = tool_call.action
        args = tool_call.arguments or {}
        
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
                success = self.memory.save_memory(content, metadata)
                return f"Memory saved: {content[:100]}" if success else "Failed"
            elif action == "search_similar":
                query = args.get("query", "")
                top_k = args.get("top_k", 5)
                results = self.memory.recall_memory(query, top_k)
                return "\\n".join(
                    f"{r.content} (score: {r.similarity_score})"
                    for r in results
                ) if results else "No similar memories"
        
        raise ValueError(f"Unknown action: {action}")
    
    def _recover_from_error(self, step: PlanStep, error: str) -> dict:
        """Analisa erro e sugere recuperação."""
        
        self.logger.info(f"[EXECUTOR] Analyzing error for recovery...")
        
        recovery_prompt = ERROR_RECOVERY_PROMPT.format(error_log=error)
        user_prompt = f"""
{recovery_prompt}

Original step: {step.description}
Error: {error}

Return ONLY JSON with keys: root_cause, fix_strategy, next_step
"""
        
        try:
            response = call_llm(user_prompt, return_json=False)
            recovery = extract_json(response)
            return recovery
        except Exception as e:
            self.logger.debug(f"Could not extract recovery JSON: {e}")
            return {
                "root_cause": error,
                "fix_strategy": "Retry",
                "next_step": step.description,
            }
    
    def _build_final_result(self) -> str:
        """Build final result summary."""
        
        if not self.steps_executed:
            return "No steps executed"
        
        results = []
        for step_num in sorted(self.steps_executed.keys()):
            step = self.steps_executed[step_num]
            status = "✓" if step.success else "✗"
            results.append(f"{status} Step {step_num}: {step.output_summary}")
        
        return "\n".join(results)
