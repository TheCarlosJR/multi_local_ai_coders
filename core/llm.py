"""
============================================================
INTERFACE COM OLLAMA (LLM Local)
============================================================
Chamadas ao modelo LLM via Ollama com:
- Tratamento de erros
- JSON parsing automático
- Retry logic
- Timeout control
============================================================
"""

import json
import logging
from typing import Optional, Dict, Any
import ollama

from core.config import (
    OLLAMA_HOST,
    OLLAMA_MODEL,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
    MAX_RETRIES,
    logger,
)
from prompts.base_prompt import BASE_SYSTEM_PROMPT

# ============================================================
# CHAMADA PADRÃO AO LLM
# ============================================================

def call_llm(
    user_prompt: str,
    system_prompt: str = BASE_SYSTEM_PROMPT,
    return_json: bool = False,
    max_retries: int = MAX_RETRIES,
) -> str:
    """
    Chama o LLM via Ollama.
    
    Args:
        user_prompt: Pergunta/instrução para o modelo
        system_prompt: Contexto do sistema (comportamento da IA)
        return_json: Se True, extrai JSON da resposta
        max_retries: Tentativas em caso de erro
    
    Returns:
        Resposta do modelo (string ou JSON parseado)
    
    Raises:
        ConnectionError: Se Ollama não responder
        json.JSONDecodeError: Se return_json=True mas resposta não é JSON válido
    """
    
    for attempt in range(max_retries):
        try:
            logger.debug(
                f"Chamando LLM (tentativa {attempt + 1}/{max_retries}): "
                f"modelo={OLLAMA_MODEL}"
            )
            
            # Chamar Ollama
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options={"temperature": LLM_TEMPERATURE},
            )
            
            content = response["message"]["content"]
            
            # Extrair JSON se solicitado
            if return_json:
                content = extract_json(content)
            
            logger.debug(f"LLM retornou: {content[:100]}...")
            return content
            
        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Resposta não é JSON válido (tentativa {attempt + 1}). "
                    f"Erro: {e}. Retentando..."
                )
                continue
            else:
                logger.error(f"JSON inválido após {max_retries} tentativas: {e}")
                raise
                
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Erro ao chamar LLM (tentativa {attempt + 1}): {e}. "
                    f"Retentando..."
                )
                continue
            else:
                logger.error(f"Erro após {max_retries} tentativas: {e}")
                raise ConnectionError(
                    f"Ollama não respondeu. "
                    f"Verifique: ollama serve em {OLLAMA_HOST}? "
                    f"Modelo '{OLLAMA_MODEL}' existe? (ollama list)"
                ) from e


# ============================================================
# UTILITÁRIOS PARA JSON
# ============================================================

def extract_json(text: str) -> Dict[str, Any]:
    """
    Extrai JSON de um texto (mesmo que contenha outras palavras).
    
    Procura por ```json ... ``` ou { ... } na resposta.
    
    Args:
        text: Texto contendo JSON
    
    Returns:
        Dicionário JSON parseado
    
    Raises:
        json.JSONDecodeError: Se nenhum JSON válido encontrado
    """
    
    # Tentar extrair JSON entre ```json ... ```
    if "```json" in text:
        json_str = text.split("```json")[1].split("```")[0].strip()
        return json.loads(json_str)
    
    # Tentar extrair entre { ... }
    if "{" in text:
        start = text.find("{")
        # Encontrar fechamento balanceado
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    json_str = text[start : i + 1]
                    return json.loads(json_str)
    
    # Se chegou aqui, não encontrou JSON
    raise json.JSONDecodeError(
        f"Nenhum JSON encontrado no texto: {text[:100]}...",
        text,
        0
    )


# ============================================================
# STREAM PARA RESPOSTAS LONGAS
# ============================================================

def call_llm_stream(
    user_prompt: str,
    system_prompt: str = BASE_SYSTEM_PROMPT,
) -> str:
    """
    Chama LLM com streaming (imprime resposta em tempo real).
    
    Útil para respostas longas ou para mostrar progresso ao usuário.
    
    Args:
        user_prompt: Pergunta/instrução
        system_prompt: Contexto do sistema
    
    Yields:
        Chunks da resposta (partes da string)
    """
    
    try:
        stream = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
            options={"temperature": LLM_TEMPERATURE},
        )
        
        for chunk in stream:
            yield chunk["message"]["content"]
            
    except Exception as e:
        logger.error(f"Erro em stream: {e}")
        raise
