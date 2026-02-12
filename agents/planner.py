"""
============================================================
AGENTE PLANEJADOR (Planning Agent)
============================================================
Responsabilidade:
- Recebe um objetivo
- Gera plano estruturado com steps ordenados
- Retorna PlanResponse validado via Pydantic
- Inclui riscos e suposi顇ões

Fluxo:
  goal → PLANNER_PROMPT → LLM → parse JSON → PlanResponse ✓
"""

import json
import logging
from typing import Optional

from core.llm import call_llm, extract_json
from core.models import PlanResponse
from core.config import logger
from prompts.planner_prompt import PLANNER_PROMPT


class PlannerAgent:
    """Agente responsável por criar planos estruturados."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def plan(self, goal: str, memory_context: str = "") -> PlanResponse:
        """
        Cria um plano para alcançar o objetivo.
        
        Args:
            goal: Objetivo a alcançar
            memory_context: Contexto de memória anterior (se houver)
        
        Returns:
            PlanResponse estruturado e validado
        
        Raises:
            json.JSONDecodeError: Se LLM retornar JSON inválido
            ValueError: Se PlanResponse falhar validacão
        """
        
        self.logger.info(f"[PLANNER] Planejando objetivo: {goal}")
        
        # Construir prompt com contexto
        context_section = ""
        if memory_context:
            context_section = f"\nRELEVANT PAST CONTEXT:\n{memory_context}\n"
        
        user_prompt = f"""
{PLANNER_PROMPT}

GOAL: {goal}
{context_section}

Respond with valid JSON only. No explanations outside JSON.
"""
        
        try:
            # Chamar LLM pedindo JSON
            response_text = call_llm(
                user_prompt=user_prompt,
                return_json=False,  # Vamos fazer parsing manual
            )
            
            self.logger.debug(f"Resposta bruta do LLM:\n{response_text}")
            
            # Extrair JSON (suporta ```json ... ```)
            response_json = extract_json(response_text)
            
            # Validar e estruturar via Pydantic
            plan = PlanResponse(**response_json)
            
            self.logger.info(
                f"[PLANNER] ✓ Plano gerado com {len(plan.steps)} steps, "
                f"{len(plan.risks)} riscos"
            )
            
            return plan
            
        except json.JSONDecodeError as e:
            self.logger.error(f"[PLANNER] Resposta não é JSON válido: {e}")
            raise ValueError(
                f"Planner retornou JSON inválido: {e}\n"
                f"Resposta: {response_text[:200]}..."
            )
        except TypeError as e:
            self.logger.error(f"[PLANNER] Validação Pydantic falhou: {e}")
            raise ValueError(
                f"Plano não atende schema esperado: {e}"
            )
        except Exception as e:
            self.logger.error(f"[PLANNER] Erro inesperado: {e}")
            raise

