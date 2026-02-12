"""
============================================================
GIT TOOL - Operações com repositório Git
============================================================
Operações Git com:
- Usando GitPython (estável e mantido)
- Detecção automática de repo
- Configuração segura de commits
- Logging detalhado
"""

import logging
from pathlib import Path
from typing import Optional

try:
    from git import Repo, GitCommandError
except ImportError:
    raise ImportError(
        "GitPython não instalado. Execute: pip install GitPython"
    )

from core.config import (
    PROJECT_ROOT,
    GIT_AUTHOR_NAME,
    GIT_AUTHOR_EMAIL,
    logger,
)

log = logging.getLogger(__name__)


def _get_repo() -> Repo:
    """
    Localiza e retorna repositório Git.
    
    Returns:
        Objeto Repo do GitPython
    
    Raises:
        ValueError: Se não estiver em repositório Git
    """
    
    try:
        repo = Repo(PROJECT_ROOT, search_parent_directories=True)
        log.info(f"✓ Repositório encontrado: {repo.working_dir}")
        return repo
    except Exception as e:
        raise ValueError(
            f"Não está em repositório Git. "
            f"Execute: git init em {PROJECT_ROOT}\n{e}"
        )


def git_status() -> str:
    """
    Retorna status atual do repositório.
    
    Returns:
        String com status (arquivos modificados, etc)
    """
    
    try:
        repo = _get_repo()
        
        # Arquivos modificados
        modified = [item.a_path for item in repo.index.diff(None)]
        untracked = repo.untracked_files
        staged = [item.a_path for item in repo.index.diff("HEAD")]
        
        lines = ["Status do repositório:"]
        if modified:
            lines.append(f"\nModificados ({len(modified)}):")
            for f in modified[:10]:  # Limitar a 10
                lines.append(f"  M {f}")
        
        if untracked:
            lines.append(f"\nNão rastreados ({len(untracked)}):")
            for f in untracked[:10]:
                lines.append(f"  ? {f}")
        
        if staged:
            lines.append(f"\nStagéd ({len(staged)}):")
            for f in staged[:10]:
                lines.append(f"  A {f}")
        
        if not modified and not untracked and not staged:
            lines.append("\n✓ Branch limpa, nada para commitar")
        
        status = "\n".join(lines)
        log.info(f"✓ Status obtido")
        return status
        
    except Exception as e:
        log.error(f"Erro ao obter status: {e}")
        raise


def git_commit(
    message: str,
    author_name: str = GIT_AUTHOR_NAME,
    author_email: str = GIT_AUTHOR_EMAIL
) -> str:
    """
    Faz commit com mensagem estruturada.
    
    Args:
        message: Mensagem de commit
        author_name: Nome do autor
        author_email: Email do autor
    
    Returns:
        SHA do commit criado
    
    Raises:
        ValueError: Se não há alterações para commitar
    """
    
    try:
        repo = _get_repo()
        
        # Verificar se há alterações
        if not repo.index.diff("HEAD") and not repo.untracked_files:
            raise ValueError("Nenhuma alteração para commitar")
        
        # Stage todas as alterações
        repo.index.add([item.a_path for item in repo.index.diff(None)])
        repo.index.add(repo.untracked_files)
        
        # Configurar autor
        with repo.config_writer() as git_config:
            git_config.set_value("user", "name", author_name)
            git_config.set_value("user", "email", author_email)
        
        # Fazer commit
        commit = repo.index.commit(message, author_name, author_email)
        
        log.info(f"✓ Commit criado: {commit.hexsha[:8]}")
        return f"Commit criado: {commit.hexsha}\n{message}"
        
    except ValueError as e:
        log.warning(f"Aviso: {e}")
        raise
    except GitCommandError as e:
        log.error(f"Erro Git: {e}")
        raise
    except Exception as e:
        log.error(f"Erro ao fazer commit: {e}")
        raise


def git_diff(staged: bool = False) -> str:
    """
    Mostra diff das alterações.
    
    Args:
        staged: Se True, mostra diff do staging area
    
    Returns:
        String com diff
    """
    
    try:
        repo = _get_repo()
        
        if staged:
            diff = repo.index.diff("HEAD")
        else:
            diff = repo.index.diff(None)
        
        if not diff:
            return "Nenhuma diferença"
        
        lines = []
        for item in diff:
            lines.append(f"{item.change_type} {item.a_path}")
        
        result = "\n".join(lines)
        log.info(f"✓ Diff obtido")
        return result
        
    except Exception as e:
        log.error(f"Erro ao obter diff: {e}")
        raise


def git_push(remote: str = "origin", branch: str = "main") -> str:
    """
    Push para repositório remoto.
    
    Args:
        remote: Nome do remote (padrão: origin)
        branch: Branch a fazer push (padrão: main)
    
    Returns:
        Resultado do push
    """
    
    try:
        repo = _get_repo()
        
        if remote not in [r.name for r in repo.remotes]:
            raise ValueError(f"Remote '{remote}' não existe")
        
        remote_obj = repo.remote(remote)
        result = remote_obj.push(branch)
        
        log.info(f"✓ Push completado para {remote}/{branch}")
        return f"Push para {remote}/{branch}: OK"
        
    except Exception as e:
        log.error(f"Erro ao fazer push: {e}")
        raise


def git_log(max_count: int = 5) -> str:
    """
    Mostra histórico de commits.
    
    Args:
        max_count: Número máximo de commits a mostrar
    
    Returns:
        String com histórico
    """
    
    try:
        repo = _get_repo()
        
        lines = [f"Últimos {max_count} commits:"]
        for i, commit in enumerate(repo.iter_commits(max_count=max_count)):
            lines.append(
                f"  {commit.hexsha[:8]} - {commit.author.name}: {commit.message.split(chr(10))[0]}"
            )
        
        result = "\n".join(lines)
        log.info(f"✓ Log obtido")
        return result
        
    except Exception as e:
        log.error(f"Erro ao obter log: {e}")
        raise

