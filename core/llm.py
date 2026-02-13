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
import time
from typing import Optional, Dict, Any
import ollama

try:
    from tenacity import (
        retry,
        wait_exponential,
        stop_after_attempt,
        retry_if_exception_type,
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

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
    Chama o LLM via Ollama com retry exponencial.
    
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
    
    # Decorador tenacity com exponential backoff
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),  # 2s, 4s, 8s...max 10s
        stop=stop_after_attempt(max_retries),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        reraise=True,
    ) if TENACITY_AVAILABLE else lambda f: f
    def _call_with_retry() -> str:
        logger.debug(
            f"Chamando LLM: modelo={OLLAMA_MODEL}, "
            f"prompt_size={len(user_prompt)} chars"
        )
        
        try:
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
            
            logger.debug(f"LLM retornou: {str(content)[:100]}...")
            return content
            
        except ConnectionError as e:
            logger.warning(f"Conexão falhou com Ollama: {e}. Retentando com backoff...")
            raise
        except TimeoutError as e:
            logger.warning(f"Timeout no LLM: {e}. Retentando com backoff...")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Resposta não é JSON válido: {e}")
            raise
    
    # Se tenacity não disponível, usar retry manual com exponential backoff
    if not TENACITY_AVAILABLE:
        logger.warning("tenacity não disponível. Usando retry manual com backoff.")
        for attempt in range(max_retries):
            try:
                return _call_with_retry()
            except (ConnectionError, TimeoutError, OSError) as e:
                if attempt < max_retries - 1:
                    wait_time = min(10, 2 ** attempt)  # 1s, 2s, 4s, 8s, 10s
                    logger.warning(
                        f"Tentativa {attempt + 1}/{max_retries} falhou. "
                        f"Aguardando {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Falha após {max_retries} tentativas")
                    raise ConnectionError(
                        f"Ollama não respondeu após {max_retries} tentativas. "
                        f"Verifique: ollama serve em {OLLAMA_HOST}? "
                        f"Modelo '{OLLAMA_MODEL}' existe? (ollama list)"
                    ) from e
            except json.JSONDecodeError as e:
                logger.error(f"JSON inválido: {e}")
                raise
    
    # Tenacity disponível - usar decorador
    return _call_with_retry()


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
