"""
Vector Store package - armazenamento de embeddings
"""

try:
    from .chromadb_store import ChromaDBStore
    __all__ = ["ChromaDBStore"]
except ImportError:
    # chromadb não instalado - será tratado por memory.py
    ChromaDBStore = None
    __all__ = []
