"""
============================================================
CONFIGURAÇÃO CENTRALIZADA DO SISTEMA
============================================================
Todas as constantes e parâmetros do agente IA em um lugar.
Customize via arquivo .env na raiz do projeto.

Variáveis suportadas:
- OLLAMA_HOST: URL do servidor Ollama
- OLLAMA_MODEL: Modelo LLM principal
- OLLAMA_EMBEDDING_MODEL: Modelo para embeddings/RAG
- LLM_TEMPERATURE: 0.0-1.0 (determinístico a criativo)
- MAX_RETRIES: Tentativas em caso de erro do Executor
- PROJECT_ROOT: Diretório raiz do projeto
- Veja .env.example para todas as opções
============================================================
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# ============================================================
# CARREGAR .env (se existir)
# ============================================================
load_dotenv()

# ============================================================
# CONFIGURAÇÃO OLLAMA (LLM Local)
# ============================================================

# URL do servidor Ollama rodando localmente
# Exemplos: "http://localhost:11434", "http://192.168.1.100:11434"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Modelo LLM para planejamento, execução e revisão
# Recomendado para código: qwen:14b, qwen-coder-2.5, mistral:latest
# Use o modelo disponível localmente via `ollama list`
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen:14b")

# Modelo para embeddings (busca semântica em memória)
# Opções: "nomic-embed-text" (4GB, qualidade alta)
#         "all-minilm" (22MB, mais rápido)
#         "" (desativar RAG/Memory)
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

# ============================================================
# PARÂMETROS DO LLM
# ============================================================

# Temperatura controla criatividade vs determinismo
# 0.0 = sempre a resposta mais provável (recomendado para código)
# 1.0 = altamente criativo, imprevisível
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

# Timeout para chamadas ao Ollama (segundos)
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))

# ============================================================
# ESTRATÉGIA DE EXECUÇÃO
# ============================================================

# Máximo de tentativas do Executor em caso de erro
# Exemplo: se falhar, tenta recuperar erro e refaz (até N vezes)
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))

# Se True, o Reviewer pode refinar o plano se resultado insatisfatório
ENABLE_REFINEMENT_LOOP = True

# ============================================================
# SISTEMA DE ARQUIVOS
# ============================================================

# Diretório raiz do projeto (para sandbox)
# Todos os arquivos acessados devem estar abaixo deste
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", ".")).resolve()

# Caminhos excluídos (não ler/modificar)
EXCLUDED_PATHS = set(
    os.getenv("EXCLUDED_PATHS", ".git,.env,.venv,__pycache__,node_modules").split(",")
)

# Máximo de linhas para ler em um arquivo
MAX_FILE_READ_LINES = int(os.getenv("MAX_FILE_READ_LINES", "10000"))

# Máximo de arquivos para listar em um diretório
MAX_DIR_LIST_FILES = int(os.getenv("MAX_DIR_LIST_FILES", "1000"))

# ============================================================
# MEMÓRIA E RAG
# ============================================================

# Caminho para banco de dados ChromaDB (embeddings)
MEMORY_DB_PATH = Path(os.getenv(
    "MEMORY_DB_PATH",
    "./vector_store/chroma_db"
)).resolve()

# Número de resultados para trazer em busca de similaridade
MEMORY_TOP_K = int(os.getenv("MEMORY_TOP_K", "5"))

# Se False, desativa buscas por memória (acelera execução)
ENABLE_MEMORY_RETRIEVAL = True

# ============================================================
# GIT
# ============================================================

# Nome do autor para commits automáticos
GIT_AUTHOR_NAME = os.getenv("GIT_AUTHOR_NAME", "AI Agent")

# Email do autor para commits automáticos
GIT_AUTHOR_EMAIL = os.getenv("GIT_AUTHOR_EMAIL", "agent@localhost")

# Se True, faz commit automático após executor bem-sucedido
AUTO_COMMIT = os.getenv("AUTO_COMMIT", "yes").lower() == "yes"

# ============================================================
# LOGGING
# ============================================================

# Nível de log: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Se True, salva logs em arquivo (logs/agent.log)
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "yes").lower() == "yes"

# Configurar logger
logger = logging.getLogger("ai_agent")
logger.setLevel(getattr(logging, LOG_LEVEL))

# Handler console
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
)
logger.addHandler(console_handler)

# Handler arquivo (opcional)
if LOG_TO_FILE:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "agent.log")
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    )
    logger.addHandler(file_handler)

# ============================================================
# SEGURANÇA - COMANDOS PROIBIDOS
# ============================================================

# Prefixos de comando que não são permitidos no terminal
FORBIDDEN_COMMANDS = set(
    cmd.strip() for cmd in os.getenv(
        "FORBIDDEN_COMMANDS",
        "rm -rf,sudo,su,format,diskpart"
    ).split(",")
)

# ============================================================
# VALIDAÇÃO DE CONFIGURAÇÃO
# ============================================================

def validate_config():
    """Verifica se a configuração está correta antes de rodar."""
    warnings = []
    
    # Avisar se modelo LLM não configurado
    if OLLAMA_MODEL == "qwen:14b":
        warnings.append(
            "[WARN] OLLAMA_MODEL usando padrao (qwen:14b). "
            "Configure OLLAMA_MODEL=qwen-coder-2.5 em .env se preferir."
        )
    
    # Avisar se Ollama não está respondendo
    try:
        import ollama
        ollama.show(OLLAMA_MODEL)
    except Exception as e:
        warnings.append(
            f"[WARN] Ollama nao respondendo em {OLLAMA_HOST} ou modelo "
            f"'{OLLAMA_MODEL}' nao existe. Execute: ollama pull {OLLAMA_MODEL}"
        )
    
    return warnings


# Log das configurações ao iniciar
if __name__ == "core.config" or __name__ == "__main__":
    logger.info(f"Config: OLLAMA_HOST={OLLAMA_HOST}")
    logger.info(f"Config: OLLAMA_MODEL={OLLAMA_MODEL}")
    logger.info(f"Config: PROJECT_ROOT={PROJECT_ROOT}")
    
    warnings = validate_config()
    for warning in warnings:
        logger.warning(warning)
