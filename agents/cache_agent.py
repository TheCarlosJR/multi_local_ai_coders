"""
============================================================
CACHE AGENT - Smart Code Snippet Caching
============================================================
Responsável por:
- Armazenar snippets bem-sucedidos em memória
- Buscar snippets similares por similaridade semântica
- Sugerir reutilização de código comprovado
- Manter histórico de sucesso de snippets
- Limpeza automática por idade

Fluxo: Planner → Cache Agent (busca similares) → Executor (tenta snippet)
       Executor (sucesso) → Cache Agent (salva com metadata) → Memory
============================================================
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json

from core.config import logger, PROJECT_ROOT, CACHE_REUSE_THRESHOLD, ENABLE_CACHE_SNIPPETS
from core.models import CodeSnippet, CacheEntry
from agents.memory_agent import MemoryAgent


class CacheAgent:
    """Agent responsável por gerenciamento inteligente de cache de código."""
    
    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.project_root = project_root
        self.logger = logger
        self.memory_agent = MemoryAgent()
        self.cache_file = project_root / ".agent_snippet_cache.json"
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Carrega cache de disco."""
        self._cache = {}
        
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file) as f:
                data = json.load(f)
                # Converter para dict de CodeSnippet
                for snippet_id, entry in data.items():
                    try:
                        snippet = CodeSnippet(**entry.get("snippet", {}))
                        self._cache[snippet_id] = {
                            "snippet": snippet,
                            "last_used": entry.get("last_used", ""),
                        }
                    except (TypeError, ValueError, KeyError):
                        pass
        except Exception as e:
            self.logger.warning(f"Erro ao carregar cache: {str(e)}")
    
    def _save_cache(self) -> None:
        """Salva cache em disco."""
        try:
            data = {}
            for snippet_id, entry in self._cache.items():
                data[snippet_id] = {
                    "snippet": entry["snippet"].model_dump(),
                    "last_used": entry.get("last_used", ""),
                }
            
            with open(self.cache_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Erro ao salvar cache: {str(e)}")
    
    def search_similar_snippets(
        self,
        goal: str,
        language: Optional[str] = None,
        threshold: Optional[float] = None
    ) -> List[CacheEntry]:
        """
        Busca snippets similares ao objetivo.
        
        Args:
            goal: Descrição do que precisa
            language: Filtrar por linguagem (py, ts, js)
            threshold: Score de similaridade mínimo
        
        Returns:
            Lista de snippets ordenados por similaridade
        """
        if not ENABLE_CACHE_SNIPPETS:
            return []
        
        if threshold is None:
            threshold = CACHE_REUSE_THRESHOLD
        
        # Buscar em ChromaDB via memory agent
        try:
            # Formatar query para busca
            query = f"code snippet for: {goal}"
            if language:
                query += f" in {language}"
            
            similar = self.memory_agent.recall_memory(query, top_k=10)
            
            # Filtrar por threshold e linguagem
            results = []
            for memory in similar:
                if memory.similarity_score >= threshold:
                    # Tentar extrair metadata "language"
                    snippet_lang = memory.metadata.get("language") if hasattr(memory, "metadata") else None
                    
                    if language is None or snippet_lang == language:
                        results.append(CacheEntry(
                            snippet_id=memory.get("id", ""),
                            snippet=CodeSnippet(
                                language=snippet_lang or "unknown",
                                code=memory.content,
                                description="",
                                metadata={},
                                usage_count=0,
                                success_rate=1.0,
                                created_at=datetime.now().isoformat()
                            ),
                            last_used=datetime.now().isoformat(),
                            similarity_score=memory.similarity_score
                        ))
            
            return sorted(results, key=lambda x: x.similarity_score or 0, reverse=True)
        
        except Exception as e:
            self.logger.warning(f"Erro ao buscar snippets similares: {str(e)}")
            return []
    
    def cache_snippet(
        self,
        code: str,
        language: str,
        goal: str,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True
    ) -> str:
        """
        Armazena um snippet no cache.
        
        Args:
            code: Código
            language: Linguagem (py, ts, js)
            goal: Para que serve
            metadata: Metadados adicionais
            success: Se foi bem-sucedido
        
        Returns:
            ID do snippet armazenado
        """
        if not ENABLE_CACHE_SNIPPETS:
            return ""
        
        try:
            snippet_id = f"{language}_{hash(code) % 10000}"
            
            snippet = CodeSnippet(
                language=language,
                code=code,
                description=goal,
                metadata=metadata or {"goal": goal},
                usage_count=1,
                success_rate=1.0 if success else 0.0,
                created_at=datetime.now().isoformat(),
                contexts=[goal]
            )
            
            # Salvar no cache local
            self._cache[snippet_id] = {
                "snippet": snippet,
                "last_used": datetime.now().isoformat(),
            }
            self._save_cache()
            
            # Salvar em ChromaDB via memory agent
            memory_metadata = {
                "language": language,
                "goal": goal,
                "success": success,
                "source": "code_cache",
                **metadata
            }
            
            self.memory_agent.save_memory(
                content=code,
                metadata=memory_metadata,
                source=f"cached_snippet_{snippet_id}"
            )
            
            self.logger.info(f"Snippet armazenado em cache: {snippet_id}")
            return snippet_id
        
        except Exception as e:
            self.logger.warning(f"Erro ao cachear snippet: {str(e)}")
            return ""
    
    def suggest_from_cache(
        self,
        goal: str,
        language: Optional[str] = None
    ) -> Optional[CodeSnippet]:
        """
        Sugere um snippet do cache para o objetivo.
        
        Args:
            goal: Objetivo
            language: Linguagem preferida
        
        Returns:
            Melhor snippet Match ou None
        """
        similar = self.search_similar_snippets(goal, language, CACHE_REUSE_THRESHOLD)
        
        if similar:
            # Retornar o melhor match
            best = similar[0]
            # Incrementar counter de uso
            best.snippet.usage_count += 1
            self._save_cache()
            
            self.logger.info(
                f"Sugerindo snippet do cache: "
                f"similarity={best.similarity_score:.2%}"
            )
            
            return best.snippet
        
        return None
    
    def update_snippet_success(self, snippet_id: str, success: bool) -> None:
        """
        Atualiza taxa de sucesso de um snippet.
        
        Args:
            snippet_id: ID do snippet
            success: Se foi bem-sucedido desta vez
        """
        if snippet_id not in self._cache:
            return
        
        try:
            snippet = self._cache[snippet_id]["snippet"]
            
            # Atualizar success_rate com média móvel
            old_rate = snippet.success_rate
            new_rate = (old_rate + (1.0 if success else 0.0)) / 2
            snippet.success_rate = new_rate
            
            self._cache[snippet_id]["last_used"] = datetime.now().isoformat()
            self._save_cache()
            
            self.logger.debug(
                f"Snippet {snippet_id} success_rate: {old_rate:.2%} → {new_rate:.2%}"
            )
        
        except Exception as e:
            self.logger.warning(f"Erro ao atualizar snippet success: {str(e)}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache."""
        try:
            total_snippets = len(self._cache)
            total_uses = sum(s["snippet"].usage_count for s in self._cache.values())
            avg_success = (
                sum(s["snippet"].success_rate for s in self._cache.values()) / total_snippets
                if total_snippets > 0
                else 0
            )
            
            # Agrupar por linguagem
            by_language = {}
            for entry in self._cache.values():
                lang = entry["snippet"].language
                by_language[lang] = by_language.get(lang, 0) + 1
            
            return {
                "total_snippets": total_snippets,
                "total_uses": total_uses,
                "avg_success_rate": avg_success,
                "by_language": by_language,
                "cache_file_size_mb": (
                    self.cache_file.stat().st_size / 1024 / 1024
                    if self.cache_file.exists()
                    else 0
                ),
            }
        
        except Exception as e:
            self.logger.warning(f"Erro ao obter stats: {str(e)}")
            return {}
    
    def cleanup_old_snippets(self, days: int = 30) -> int:
        """
        Remove snippets não utilizados há mais de X dias.
        
        Returns:
            Número de snippets removidos
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            removed_count = 0
            
            snippets_to_remove = []
            for snippet_id, entry in self._cache.items():
                last_used_str = entry.get("last_used", "")
                if last_used_str:
                    try:
                        last_used = datetime.fromisoformat(last_used_str)
                        if last_used < cutoff_date:
                            snippets_to_remove.append(snippet_id)
                    except (ValueError, TypeError):
                        pass
            
            for snippet_id in snippets_to_remove:
                del self._cache[snippet_id]
                removed_count += 1
            
            if removed_count > 0:
                self._save_cache()
                self.logger.info(f"Removidos {removed_count} snippets não usados")
            
            return removed_count
        
        except Exception as e:
            self.logger.warning(f"Erro ao fazer cleanup: {str(e)}")
            return 0
    
    def clear_cache(self) -> None:
        """Limpa todo o cache."""
        try:
            self._cache = {}
            self._save_cache()
            self.logger.info("Cache limpo")
        except Exception as e:
            self.logger.warning(f"Erro ao limpar cache: {str(e)}")
    
    def is_cache_enabled(self) -> bool:
        """Verifica se cache está habilitado."""
        return ENABLE_CACHE_SNIPPETS
