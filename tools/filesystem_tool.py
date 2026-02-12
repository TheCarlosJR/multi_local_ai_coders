"""
============================================================
FILESYSTEM TOOL - Operações com arquivos
============================================================
Operações seguras de leitura/escrita com:
- Validação de caminhos (sandbox PROJECT_ROOT)
- Limite de tamanho para leitura
- Suporte a múltiplos encodings
"""

import logging
from pathlib import Path
from typing import List

from core.config import (
    PROJECT_ROOT,
    EXCLUDED_PATHS,
    MAX_FILE_READ_LINES,
    MAX_DIR_LIST_FILES,
    logger,
)

log = logging.getLogger(__name__)


def _validate_path(path_str: str) -> Path:
    """
    Valida caminho para evitar saída de PROJECT_ROOT (sandbox).
    
    Args:
        path_str: Caminho a validar
    
    Returns:
        Path validado e resolvido
    
    Raises:
        ValueError: Se caminho está fora de PROJECT_ROOT ou excluído
    """
    
    path = Path(path_str).resolve()
    
    # Verificar se está dentro de PROJECT_ROOT
    try:
        path.relative_to(PROJECT_ROOT)
    except ValueError:
        raise ValueError(
            f"Caminho fora do PROJECT_ROOT: {path}. "
            f"Limite: {PROJECT_ROOT}"
        )
    
    # Verificar se está na lista de excludeds
    for excluded in EXCLUDED_PATHS:
        if excluded in str(path):
            raise ValueError(
                f"Caminho está na lista de exclusão: {path}"
            )
    
    return path


def read_file(path: str, encoding: str = "utf-8") -> str:
    """
    Lê arquivo com segurança.
    
    Args:
        path: Caminho do arquivo
        encoding: Codificação (utf-8, latin-1, etc)
    
    Returns:
        Conteúdo do arquivo
    
    Raises:
        FileNotFoundError: Se arquivo não existe
        ValueError: Se arquivo muito grande
    """
    
    try:
        file_path = _validate_path(path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não existe: {path}")
        
        if not file_path.is_file():
            raise ValueError(f"Não é arquivo: {path}")
        
        # Ler arquivo
        content = file_path.read_text(encoding=encoding)
        lines = content.split("\n")
        
        if len(lines) > MAX_FILE_READ_LINES:
            log.warning(
                f"Arquivo truncado: {len(lines)} linhas > {MAX_FILE_READ_LINES}"
            )
            content = "\n".join(lines[:MAX_FILE_READ_LINES])
            content += f"\n\n[... arquivo truncado, {len(lines) - MAX_FILE_READ_LINES} linhas restantes ...]"
        
        log.info(f"✓ Lido: {path} ({len(lines)} linhas)")
        return content
        
    except Exception as e:
        log.error(f"Erro ao ler {path}: {e}")
        raise


def write_file(path: str, content: str, encoding: str = "utf-8") -> str:
    """
    Escreve arquivo com segurança.
    
    Args:
        path: Caminho do arquivo
        content: Conteúdo a escrever
        encoding: Codificação
    
    Returns:
        Mensagem de sucesso
    
    Raises:
        ValueError: Se caminho inválido ou arquivo protegido
    """
    
    try:
        file_path = _validate_path(path)
        
        # Criar diretório pai se não existir
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Escrever
        file_path.write_text(content, encoding=encoding)
        
        log.info(f"✓ Escrito: {path} ({len(content)} bytes)")
        return f"Arquivo salvo: {path}"
        
    except Exception as e:
        log.error(f"Erro ao escrever {path}: {e}")
        raise


def list_dir(path: str = ".") -> str:
    """
    Lista conteúdo de diretório com segurança.
    
    Args:
        path: Caminho do diretório
    
    Returns:
        String formatada com conteúdo
    """
    
    try:
        dir_path = _validate_path(path)
        
        if not dir_path.exists():
            raise FileNotFoundError(f"Diretório não existe: {path}")
        
        if not dir_path.is_dir():
            raise ValueError(f"Não é diretório: {path}")
        
        # Listar conteúdo
        items = list(dir_path.iterdir())
        
        if len(items) > MAX_DIR_LIST_FILES:
            log.warning(
                f"Diretório truncado: {len(items)} arquivos > {MAX_DIR_LIST_FILES}"
            )
            items = items[:MAX_DIR_LIST_FILES]
        
        # Formatar output
        lines = [f"Conteúdo de {path}:"]
        for item in sorted(items):
            item_type = "[DIR]" if item.is_dir() else "[FILE]"
            size = ""
            if item.is_file():
                size = f" ({item.stat().st_size} bytes)"
            lines.append(f"  {item_type} {item.name}{size}")
        
        result = "\n".join(lines)
        log.info(f"✓ Listado: {path} ({len(items)} itens)")
        return result
        
    except Exception as e:
        log.error(f"Erro ao listar {path}: {e}")
        raise

