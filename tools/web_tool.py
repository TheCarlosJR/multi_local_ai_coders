"""
============================================================
WEB TOOL - Operações de web scraping
============================================================
Fetch de URLs com:
- Timeout control
- Error handling
- HTML parsing com BeautifulSoup
"""

import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

from core.config import logger

log = logging.getLogger(__name__)


def fetch_url(url: str, timeout: int = 10, text_only: bool = True) -> str:
    """
    Busca conteúdo de uma URL com segurança.
    
    Args:
        url: URL a buscar
        timeout: Timeout em segundos
        text_only: Se True, retorna apenas texto (limpo de HTML)
    
    Returns:
        Conteúdo da página
    
    Raises:
        requests.RequestException: Se erro na requisição
    """
    
    try:
        # Validar URL
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"URL inválida (sem http/https): {url}")
        
        log.info(f"Buscando: {url}")
        
        # Fazer requisição
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        if text_only:
            # Extrair texto limpo
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remover scripts e styles
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Obter texto
            text = soup.get_text()
            
            # Limpar whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)
            
            log.info(f"✓ Busca completada ({len(text)} chars)")
            return text
        else:
            # Retornar HTML bruto
            log.info(f"✓ Busca completada ({len(response.text)} chars)")
            return response.text
        
    except requests.exceptions.Timeout:
        log.error(f"Timeout ao acessar {url}")
        raise
    except requests.exceptions.RequestException as e:
        log.error(f"Erro ao acessar {url}: {e}")
        raise
    except Exception as e:
        log.error(f"Erro ao processar conteúdo: {e}")
        raise


def fetch_url_raw(url: str, timeout: int = 10) -> str:
    """
    Busca conteúdo bruto (HTML) de uma URL.
    
    Args:
        url: URL a buscar
        timeout: Timeout em segundos
    
    Returns:
        HTML bruto
    """
    
    return fetch_url(url, timeout=timeout, text_only=False)

