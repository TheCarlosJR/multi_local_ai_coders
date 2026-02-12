"""
============================================================
TERMINAL TOOL - Execução de comandos
============================================================
Execução segura de comandos com:
- Blacklist de comandos perigosos
- Detecção automática de shell (Windows/Unix)
- Captura de stdout/stderr
- Timeout control
"""

import subprocess
import platform
import logging
from typing import Tuple

from core.config import FORBIDDEN_COMMANDS, logger

log = logging.getLogger(__name__)


def _validate_command(cmd: str) -> None:
    """
    Valida comando para evitar operações perigosas.
    
    Args:
        cmd: Comando a executar
    
    Raises:
        ValueError: Se comando está na blacklist
    """
    
    cmd_lower = cmd.lower()
    
    for forbidden in FORBIDDEN_COMMANDS:
        if forbidden.lower() in cmd_lower:
            raise ValueError(
                f"Comando proibido: '{forbidden}' detectado em '{cmd}'"
            )
    
    # Avisos adicionais
    dangerous_patterns = [
        "rm -rf",
        "deltree",
        "format ",
        "diskpart",
        "sudo ",
    ]
    
    for pattern in dangerous_patterns:
        if pattern.lower() in cmd_lower:
            log.warning(f"Comando potencialmente perigoso: {cmd}")


def run_cmd(
    cmd: str,
    timeout: int = 30,
    cwd: str = None
) -> str:
    """
    Executa comando no shell com segurança.
    
    Args:
        cmd: Comando a executar
        timeout: Timeout em segundos
        cwd: Diretório de trabalho
    
    Returns:
        Output do comando (stdout + stderr)
    
    Raises:
        ValueError: Se comando proibido
        subprocess.TimeoutExpired: Se timeout excedido
    """
    
    # Validar
    _validate_command(cmd)
    
    # Detectar shell
    system = platform.system()
    shell = "powershell" if system == "Windows" else "/bin/bash"
    
    log.info(f"Executando: {cmd} (shell: {shell})")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        
        if result.returncode != 0:
            log.warning(f"Comando retornou código {result.returncode}")
        else:
            log.info(f"✓ Comando sucesso")
        
        return output
        
    except subprocess.TimeoutExpired:
        log.error(f"Timeout ao executar: {cmd}")
        raise
    except Exception as e:
        log.error(f"Erro ao executar {cmd}: {e}")
        raise


def run_cmd_with_output(cmd: str) -> Tuple[int, str, str]:
    """
    Versão alternativa que retorna (return_code, stdout, stderr).
    
    Útil para processar saída estruturada.
    """
    
    _validate_command(cmd)
    
    system = platform.system()
    shell = "powershell" if system == "Windows" else "/bin/bash"
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        return result.returncode, result.stdout, result.stderr
        
    except Exception as e:
        log.error(f"Erro: {e}")
        return -1, "", str(e)

