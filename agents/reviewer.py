"""
============================================================
AGENTE REVISOR (Code Review Agent)
============================================================
Responsabilidade:
- Recebe resultado da execução
- Avalia se objetivo foi alcançado
- Detecta problemas, bugs, segurança
- Recomenda refinamento se necessário
- Retorna ReviewResponse estruturado

Fluxo:
  ExecutorResponse + goal → REVIEWER_PROMPT → LLM 
    ↓
  → parse JSON → ReviewResponse ✓
"""

import json
import logging

from core.llm import call_llm, extract_json
from core.models import ReviewResponse, ReviewStatus
from core.config import logger
from prompts.reviewer_prompt import REVIEWER_PROMPT


class ReviewerAgent:
    """Agente responsável por revisar o trabalho executado."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def review(
        self,
        goal: str,
        execution_result: str,
        plan_description: str = ""
    ) -> ReviewResponse:
        """
        Revisa o resultado da execução contra o objetivo.
        
        Args:
            goal: Objetivo original
            execution_result: Resultado da execução
            plan_description: Descrição do plano (para contexto)
        
        Returns:
            ReviewResponse estruturado e validado
        
        Raises:
            json.JSONDecodeError: Se LLM retornar JSON inválido
            ValueError: Se ReviewResponse falhar validação
        """
        
        self.logger.info(f"[REVIEWER] Revisando resultado contra objetivo: {goal}")
        
        # Construir prompt com contexto opcional
        plan_section = ""
        if plan_description:
            plan_section = f"\nPLAN DESCRIPTION:\n{plan_description}"
        
        user_prompt = f"""
{REVIEWER_PROMPT}

ORIGINAL GOAL:
{goal}

EXECUTION RESULT:
{execution_result}
{plan_section}

Analyze if goal was achieved. Return JSON only. No explanations outside JSON.
"""
        
        try:
            # Chamar LLM
            response_text = call_llm(user_prompt=user_prompt, return_json=False)
            
            self.logger.debug(f"Resposta bruta do LLM:\n{response_text}")
            
            # Extrair JSON
            response_json = extract_json(response_text)
            
            # Mapear status string para enum
            status_str = response_json.get("status", "needs_revision").lower()
            if status_str == "approved":
                response_json["status"] = ReviewStatus.APPROVED
            elif status_str == "needs_revision":
                response_json["status"] = ReviewStatus.NEEDS_REFINEMENT
            else:
                response_json["status"] = ReviewStatus.FAILED
            
            # Validar via Pydantic
            review = ReviewResponse(**response_json)
            
            self.logger.info(
                f"[REVIEWER] ✓ Revisão concluída: "
                f"status={review.status.value}, "
                f"confidence={review.confidence:.2f}, "
                f"issues={len(review.issues)}"
            )
            
            return review
            
        except json.JSONDecodeError as e:
            self.logger.error(f"[REVIEWER] Resposta não é JSON válido: {e}")
            raise ValueError(
                f"Reviewer retornou JSON inválido: {e}\n"
                f"Resposta: {response_text[:200]}..."
            )
        except (TypeError, KeyError) as e:
            self.logger.error(f"[REVIEWER] Validação Pydantic falhou: {e}")
            raise ValueError(
                f"Review não atende schema esperado: {e}"
            )
        except Exception as e:
            self.logger.error(f"[REVIEWER] Erro inesperado: {e}")
            raise

