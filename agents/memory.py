"""
============================================================
MEMORY AGENT - Retrieval-Augmented Generation (RAG)
============================================================
Integração com ChromaDB para:
- Armazenar embeddings de contexto passado
- Buscar informações similares por semântica
- Informar Planner com contexto relevante

Usa Ollama embeddings para manter tudo local.
"""

import logging
from typing import List, Optional

from core.llm import call_llm
from core.models import MemoryEntry, MemorySearchResult
from core.config import (
    OLLAMA_EMBEDDING_MODEL,
    MEMORY_TOP_K,
    MEMORY_DB_PATH,
    logger,
)
from prompts.memory_retrieval_prompt import MEMORY_RETRIEVAL_PROMPT
from vector_store.chromadb_store import ChromaDBStore

log = logging.getLogger(__name__)


class MemoryAgent:
    """Agente responsável por gerenciar memória e contexto do agente."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        try:
            self.db = ChromaDBStore(
                persist_directory=str(MEMORY_DB_PATH),
                embedding_model=OLLAMA_EMBEDDING_MODEL,
            )
            self.logger.info(f"✓ ChromaDB inicializado em {MEMORY_DB_PATH}")
        except Exception as e:
            self.logger.warning(f"ChromaDB não disponível: {e}. RAG desativado.")
            self.db = None
    
    def save_memory(self, content: str, metadata: dict = None, source: str = "") -> bool:
        """
        Armazena informação na memória (com embedding).
        
        Args:
            content: Texto a memorizar
            metadata: Tags/metadados (ex: {'task': 'git', 'status': 'success'})
            source: Origem (ex: 'plan_review_1', 'error_recovery')
        
        Returns:
            True se sucesso, False caso contrário
        """
        
        if not self.db:
            self.logger.warning("ChromaDB não disponível, memória não salva")
            return False
        
        try:
            entry = MemoryEntry(
                content=content,
                metadata=metadata or {},
                source=source,
            )
            
            self.db.add_document(
                text=entry.content,
                metadata={**entry.metadata, "source": entry.source},
            )
            
            self.logger.info(f"✓ Memória salva: {source}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar memória: {e}")
            return False
    
    def recall_memory(self, query: str, top_k: int = MEMORY_TOP_K) -> List[MemorySearchResult]:
        """
        Busca informações similares na memória.
        
        Args:
            query: Pergunta/contexto a buscar
            top_k: Número de resultados
        
        Returns:
            Lista de resultados similares
        """
        
        if not self.db:
            self.logger.warning("ChromaDB não disponível")
            return []
        
        try:
            # Primeiro pedir ao LLM para gerar keywords
            keywords = self._generate_search_keywords(query)
            
            # Depois buscar no DB
            results = self.db.search(
                query_text=keywords,
                n_results=top_k,
            )
            
            memory_results = []
            for doc, similarity in results:
                memory_results.append(
                    MemorySearchResult(
                        content=doc,
                        similarity_score=similarity,
                        source="memory_db",
                    )
                )
            
            self.logger.info(f"✓ Memória recuperada: {len(memory_results)} resultados")
            return memory_results
            
        except Exception as e:
            self.logger.error(f"Erro ao recuperar memória: {e}")
            return []
    
    def _generate_search_keywords(self, query: str) -> str:
        """
        Usa LLM para gerar keywords de busca otimizados.
        
        Melhora a qualidade da busca semântica.
        """
        
        try:
            user_prompt = f"""
{MEMORY_RETRIEVAL_PROMPT}

QUERY: {query}

Generate search keywords. Return JSON with "keywords" as list of strings.
"""
            
            response = call_llm(user_prompt, return_json=False)
            
            # Extrair keywords
            if "keywords" in response.lower():
                # Se retornou JSON, usar isso
                import json
                data = json.loads(response[response.find('{'):response.rfind('}')+1])
                keywords = " ".join(data.get("keywords", []))
            else:
                # Senão usar query original
                keywords = query
            
            return keywords
            
        except:
            # Em caso de erro, usar query original
            return query
    
    def get_context(self, goal: str) -> str:
        """
        Gera contexto textual para informar o Planner.
        
        Args:
            goal: Objetivo atual
        
        Returns:
            String com contexto relevante
        """
        
        results = self.recall_memory(goal, top_k=3)
        
        if not results:
            return ""
        
        lines = ["RELEVANT CONTEXT FROM MEMORY:"]
        for r in results:
            lines.append(f"- {r.content[:100]}... (similarity: {r.similarity_score:.2f})")
        
        return "\n".join(lines)

