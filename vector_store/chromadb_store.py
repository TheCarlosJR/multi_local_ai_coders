"""
============================================================
CHROMADB VECTOR STORE - Armazenamento de Embeddings
============================================================
Integração com ChromaDB e Ollama embeddings para RAG.

Responsabilidade:
- Armazenar documentos com embeddings
- Buscar por similaridade semântica
- Persistir em disco
"""

import logging
from typing import List, Tuple, Optional
from pathlib import Path

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from core.config import logger

log = logging.getLogger(__name__)


class ChromaDBStore:
    """
    Vector store usando ChromaDB + Ollama embeddings.
    """
    
    def __init__(
        self,
        persist_directory: str = "./vector_store/chroma_db",
        embedding_model: str = "nomic-embed-text",
        collection_name: str = "agent_memories",
    ):
        """
        Inicializa ChromaDB com persistência em disco.
        
        Args:
            persist_directory: Diretório para salvar embeddings
            embedding_model: Modelo Ollama para embeddings
            collection_name: Nome da collection
        
        Raises:
            ImportError: Se ChromaDB ou Ollama não estiverem instalados
        """
        
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "ChromaDB não instalado. Execute: pip install chromadb"
            )
        
        if not OLLAMA_AVAILABLE:
            raise ImportError(
                "Ollama client não instalado. Execute: pip install ollama"
            )
        
        self.logger = logging.getLogger(__name__)
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        
        try:
            # Criar diretório se não existir
            Path(persist_directory).mkdir(parents=True, exist_ok=True)
            
            # Inicializar ChromaDB com PersistentClient (API nova)
            self.client = chromadb.PersistentClient(path=persist_directory)
            
            # Obter ou criar collection com nova API
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            self.logger.info(
                f"✓ ChromaDB inicializado: {collection_name} em {persist_directory}"
            )
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar ChromaDB: {e}")
            raise
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        Gera embedding via Ollama.
        
        Args:
            text: Texto a embutir
        
        Returns:
            Lista de floats (embedding)
        """
        
        try:
            response = ollama.embeddings(
                model=self.embedding_model,
                prompt=text,
            )
            return response.get("embedding", [])
        except Exception as e:
            self.logger.error(f"Erro ao gerar embedding: {e}")
            raise
    
    def add_document(
        self,
        text: str,
        metadata: dict = None,
        doc_id: str = None,
    ) -> str:
        """
        Adiciona documento com embedding à collection.
        
        Args:
            text: Conteúdo do documento
            metadata: Metadados adicionais (tags, source, etc)
            doc_id: ID único (gerado automaticamente se None)
        
        Returns:
            ID do documento
        """
        
        try:
            # Gerar ID se não fornecido
            if not doc_id:
                import uuid
                doc_id = str(uuid.uuid4())
            
            # Gerar embedding
            embedding = self._get_embedding(text)
            
            # Adicionar à collection
            self.collection.add(
                ids=[doc_id],
                documents=[text],
                embeddings=[embedding],
                metadatas=[metadata or {}],
            )
            
            # Persistir
            self.client.persist()
            
            self.logger.info(f"✓ Documento adicionado: {doc_id}")
            return doc_id
            
        except Exception as e:
            self.logger.error(f"Erro ao adicionar documento: {e}")
            raise
    
    def search(
        self,
        query_text: str,
        n_results: int = 5,
    ) -> List[Tuple[str, float]]:
        """
        Busca por documentos similares.
        
        Args:
            query_text: Texto a buscar
            n_results: Número de resultados
        
        Returns:
            Lista de (documento, similaridade)
        """
        
        try:
            # Gerar embedding da query
            query_embedding = self._get_embedding(query_text)
            
            # Buscar na collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "distances"]
            )
            
            # Processar resultados
            documents = results.get("documents", [[]])[0]
            distances = results.get("distances", [[]])[0]
            
            # Converter distância para similaridade (cosine: 0=igual, 2=oposto)
            # Normalizar para 0-1 (1=muito similar, 0=não similar)
            similarities = [(1 - d/2) for d in distances]
            
            output = list(zip(documents, similarities))
            
            self.logger.info(f"✓ Busca completada: {len(output)} resultados")
            return output
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar: {e}")
            raise
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Remove documento da collection.
        
        Args:
            doc_id: ID do documento
        
        Returns:
            True se sucesso
        """
        
        try:
            self.collection.delete(ids=[doc_id])
            self.client.persist()
            self.logger.info(f"✓ Documento deletado: {doc_id}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao deletar: {e}")
            return False
    
    def clear_collection(self) -> bool:
        """
        Limpa toda a collection (use com cuidado!).
        
        Returns:
            True se sucesso
        """
        
        try:
            # Listar todos os IDs
            all_results = self.collection.get()
            ids = all_results.get("ids", [])
            
            # Deletar tudo
            if ids:
                self.collection.delete(ids=ids)
                self.client.persist()
            
            self.logger.info(f"✓ Collection limpa ({len(ids)} documentos removidos)")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao limpar: {e}")
            return False
    
    def get_stats(self) -> dict:
        """
        Retorna estatísticas da collection.
        
        Returns:
            Dict com count, etc
        """
        
        try:
            results = self.collection.get()
            count = len(results.get("ids", []))
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "embedding_model": self.embedding_model,
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter stats: {e}")
            return {}
    
    # ============================================================
    # CONTROLE DE LIMITES (ChromaDB Management)
    # ============================================================
    
    def enforce_document_limit(self, max_documents: int) -> int:
        """
        Enforce máximo de documentos mantendo os mais recentes.
        Remove documentos antigos se ultrapassar limite.
        
        Args:
            max_documents: Máximo de documentos permitido
        
        Returns:
            Número de documentos removidos
        """
        if max_documents <= 0:
            return 0
        
        try:
            results = self.collection.get()
            current_count = len(results.get("ids", []))
            
            if current_count <= max_documents:
                return 0
            
            # Número de docs a remover
            to_remove_count = current_count - max_documents
            
            # IDs dos documentos (assumindo ordem de inserção)
            all_ids = results.get("ids", [])
            ids_to_remove = all_ids[:to_remove_count]
            
            if ids_to_remove:
                self.collection.delete(ids=ids_to_remove)
                self.client.persist()
                self.logger.info(
                    f"✓ Limit enforcement: removidos {len(ids_to_remove)} docs "
                    f"({current_count} → {max_documents})"
                )
            
            return len(ids_to_remove)
        
        except Exception as e:
            self.logger.error(f"Erro ao enforce limit: {e}")
            return 0
    
    def cleanup_old_documents(self, retention_days: int = 30) -> int:
        """
        Remove documentos não acessados há mais de X dias.
        
        Args:
            retention_days: Dias para manter documentos
        
        Returns:
            Número de documentos removidos
        """
        if retention_days <= 0:
            return 0
        
        try:
            from datetime import datetime, timedelta
            
            results = self.collection.get(include=["metadatas"])
            ids = results.get("ids", [])
            metadatas = results.get("metadatas", [])
            
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            ids_to_remove = []
            
            for doc_id, metadata in zip(ids, metadatas):
                if metadata:
                    # Tentar obter data de criação/acesso
                    created_at_str = metadata.get("created_at")
                    
                    if created_at_str:
                        try:
                            created_at = datetime.fromisoformat(created_at_str)
                            if created_at < cutoff_date:
                                ids_to_remove.append(doc_id)
                        except:
                            pass
            
            if ids_to_remove:
                self.collection.delete(ids=ids_to_remove)
                self.client.persist()
                self.logger.info(
                    f"✓ Cleanup: removidos {len(ids_to_remove)} docs antigos"
                )
            
            return len(ids_to_remove)
        
        except Exception as e:
            self.logger.error(f"Erro ao fazer cleanup: {e}")
            return 0
    
    def get_storage_size_mb(self) -> float:
        """
        Retorna tamanho do banco de dados em MB.
        
        Returns:
            Tamanho em MB
        """
        try:
            from pathlib import Path
            
            # Encontrar diretório do ChromaDB
            # Isso é aproximado - depende da estrutura interna do ChromaDB
            persist_path = getattr(self.client, "_path", None)
            
            if persist_path and Path(persist_path).exists():
                total_size = 0
                for item in Path(persist_path).rglob("*"):
                    if item.is_file():
                        total_size += item.stat().st_size
                
                return total_size / (1024 * 1024)
        
        except Exception as e:
            self.logger.debug(f"Erro ao calcular tamanho: {e}")
        
        return 0.0
    
    def check_limits(
        self,
        max_documents: int = 5000,
        max_size_mb: float = 500.0,
    ) -> dict:
        """
        Verifica se limites estão sendo respeitados.
        
        Args:
            max_documents: Máximo de documentos
            max_size_mb: Máximo de tamanho em MB
        
        Returns:
            Dict com status dos limites
        """
        try:
            results = self.collection.get()
            doc_count = len(results.get("ids", []))
            size_mb = self.get_storage_size_mb()
            
            status = {
                "document_count": doc_count,
                "size_mb": size_mb,
                "limits": {
                    "max_documents": max_documents,
                    "max_size_mb": max_size_mb,
                },
                "status": {
                    "documents_ok": doc_count <= max_documents if max_documents > 0 else True,
                    "size_ok": size_mb <= max_size_mb if max_size_mb > 0 else True,
                },
            }
            
            if not status["status"]["documents_ok"]:
                self.logger.warning(
                    f"⚠ Document limit exceeded: {doc_count} > {max_documents}"
                )
            
            if not status["status"]["size_ok"]:
                self.logger.warning(
                    f"⚠ Size limit exceeded: {size_mb:.1f}MB > {max_size_mb}MB"
                )
            
            return status
        
        except Exception as e:
            self.logger.error(f"Erro ao verificar limites: {e}")
            return {}


