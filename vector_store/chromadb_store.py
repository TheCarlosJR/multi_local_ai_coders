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
except ImportError:
    raise ImportError(
        "ChromaDB não instalado. Execute: pip install chromadb"
    )

try:
    import ollama
except ImportError:
    raise ImportError(
        "Ollama client não instalado. Execute: pip install ollama"
    )

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
        """
        
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

