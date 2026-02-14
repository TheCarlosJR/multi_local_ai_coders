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


# ============================================================
# INLINE CODE COMPLETION
# ============================================================

# Import inline completion configs (lazy to avoid circular import)
def _get_completion_config():
    """Get completion configuration lazily."""
    from core.config import (
        OLLAMA_COMPLETION_MODEL,
        COMPLETION_TEMPERATURE,
        COMPLETION_MAX_TOKENS,
    )
    return OLLAMA_COMPLETION_MODEL, COMPLETION_TEMPERATURE, COMPLETION_MAX_TOKENS


def get_code_completions(
    file_path: str,
    content: str,
    line: int,
    column: int,
    prefix: str = "",
    num_suggestions: int = 3,
) -> list:
    """
    Gera completações de código inline para IDE.
    
    Args:
        file_path: Caminho do arquivo sendo editado
        content: Conteúdo completo do arquivo
        line: Número da linha atual (1-indexed)
        column: Posição da coluna
        prefix: Texto já digitado na linha atual
        num_suggestions: Número de sugestões a retornar
    
    Returns:
        Lista de dicts com 'completion' e 'score'
    """
    
    completion_model, completion_temp, max_tokens = _get_completion_config()
    
    # Extrair contexto relevante (linhas anteriores para contexto)
    lines = content.split('\n')
    
    # Pegar 20 linhas anteriores como contexto (ou menos se arquivo menor)
    start_line = max(0, line - 21)
    context_lines = lines[start_line:line]
    
    # Linha atual até o cursor
    current_line = lines[line - 1][:column] if line <= len(lines) else ""
    
    # Montar contexto
    context = '\n'.join(context_lines)
    if current_line:
        context += '\n' + current_line
    
    # Detectar linguagem pela extensão
    extension = file_path.split('.')[-1] if '.' in file_path else 'txt'
    lang_map = {
        'py': 'Python',
        'js': 'JavaScript', 
        'ts': 'TypeScript',
        'java': 'Java',
        'go': 'Go',
        'rs': 'Rust',
        'cpp': 'C++',
        'c': 'C',
        'rb': 'Ruby',
        'php': 'PHP',
        'cs': 'C#',
        'kt': 'Kotlin',
        'sh': 'Shell',
    }
    language = lang_map.get(extension, extension.upper())
    
    # Prompt otimizado para completação
    completion_prompt = f"""Complete the following {language} code. 
Return ONLY the code that should come next (no explanations, no markdown).
Continue naturally from where the code ends.

```{extension}
{context}
```

Complete the next 1-3 lines of code:"""

    system_prompt = """You are a code completion engine. 
Rules:
- Return ONLY code, no explanations
- No markdown formatting (no ```)
- Complete naturally based on context
- Keep completions short (1-3 lines max)
- Match the existing code style"""

    try:
        # Usar modelo de completação (pode ser diferente do principal)
        response = ollama.chat(
            model=completion_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": completion_prompt},
            ],
            options={
                "temperature": completion_temp,
                "num_predict": max_tokens,
            },
        )
        
        completion_text = response["message"]["content"].strip()
        
        # Limpar resposta (remover markdown se presente)
        completion_text = _clean_completion(completion_text, extension)
        
        # Gerar múltiplas sugestões com pequena variação de temperatura
        suggestions = [
            {"completion": completion_text, "score": 0.9}
        ]
        
        # Se precisar de mais sugestões, chamar novamente com temperatura maior
        if num_suggestions > 1:
            for i in range(min(num_suggestions - 1, 2)):
                try:
                    alt_response = ollama.chat(
                        model=completion_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": completion_prompt},
                        ],
                        options={
                            "temperature": completion_temp + 0.1 * (i + 1),
                            "num_predict": max_tokens,
                        },
                    )
                    alt_text = alt_response["message"]["content"].strip()
                    alt_text = _clean_completion(alt_text, extension)
                    
                    # Evitar duplicatas
                    if alt_text != completion_text:
                        suggestions.append({
                            "completion": alt_text,
                            "score": 0.7 - (0.1 * i)
                        })
                except Exception:
                    pass  # Ignorar falhas em sugestões alternativas
        
        logger.debug(f"Completações geradas: {len(suggestions)}")
        return suggestions
        
    except ConnectionError as e:
        logger.warning(f"Completação falhou (conexão): {e}")
        return []
    except Exception as e:
        logger.error(f"Erro em completação: {e}")
        return []


def _clean_completion(text: str, extension: str) -> str:
    """
    Remove formatação markdown e limpa a completação.
    
    Args:
        text: Texto da completação
        extension: Extensão do arquivo
    
    Returns:
        Texto limpo
    """
    # Remover markdown code blocks
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            # Remover identificador de linguagem na primeira linha
            if '\n' in text:
                first_line = text.split('\n')[0].strip().lower()
                # Lista de identificadores de linguagem comuns em markdown
                lang_ids = ['python', 'py', 'javascript', 'js', 'typescript', 'ts', 
                            'java', 'go', 'rust', 'cpp', 'c', 'ruby', 'php', 
                            'html', 'css', 'sql', 'bash', 'sh', 'json', 'yaml', 'yml']
                if first_line in lang_ids or first_line == extension.lower():
                    text = '\n'.join(text.split('\n')[1:])
            elif text.strip() == extension or text.strip() == extension.upper():
                # Caso especial: apenas o nome da linguagem sem código
                text = ''
    
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    
    return text.strip()


def get_single_completion(
    file_path: str,
    content: str, 
    line: int,
    column: int,
) -> str:
    """
    Versão simplificada que retorna apenas uma completação.
    Útil para integração mais simples.
    
    Args:
        file_path: Caminho do arquivo
        content: Conteúdo do arquivo
        line: Linha atual
        column: Coluna atual
    
    Returns:
        String com a completação ou vazio se falhar
    """
    suggestions = get_code_completions(file_path, content, line, column, num_suggestions=1)
    return suggestions[0]["completion"] if suggestions else ""
