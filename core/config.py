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
# INLINE COMPLETION (Continue.dev / IDE)
# ============================================================

# Modelo para completação inline (sugestões em tempo real)
# Use modelo menor para respostas rápidas: qwen2.5-coder:1.5b, codellama:7b
# Por padrão, usa o modelo principal (OLLAMA_MODEL)
OLLAMA_COMPLETION_MODEL = os.getenv("OLLAMA_COMPLETION_MODEL", OLLAMA_MODEL)

# Temperatura para completações (0.0 = determinístico, ideal para code completion)
COMPLETION_TEMPERATURE = float(os.getenv("COMPLETION_TEMPERATURE", "0.1"))

# Máximo de tokens na resposta de completação (limitar para velocidade)
COMPLETION_MAX_TOKENS = int(os.getenv("COMPLETION_MAX_TOKENS", "150"))

# Timeout para completações (deve ser curto para UX)
COMPLETION_TIMEOUT = int(os.getenv("COMPLETION_TIMEOUT", "5"))

# Número máximo de sugestões de completação
COMPLETION_MAX_SUGGESTIONS = int(os.getenv("COMPLETION_MAX_SUGGESTIONS", "3"))

# Ativar/desativar completação inline
ENABLE_INLINE_COMPLETION = os.getenv("ENABLE_INLINE_COMPLETION", "true").lower() == "true"

# Debounce em milissegundos (para evitar chamadas excessivas)
COMPLETION_DEBOUNCE_MS = int(os.getenv("COMPLETION_DEBOUNCE_MS", "300"))

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

# Número de threads para execução paralela de steps
EXECUTOR_MAX_WORKERS = int(os.getenv("EXECUTOR_MAX_WORKERS", "4"))

# Timeout em segundos por step de execução
EXECUTOR_STEP_TIMEOUT = int(os.getenv("EXECUTOR_STEP_TIMEOUT", "300"))

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

# Limite máximo de documentos armazenados em ChromaDB
# 0 = sem limite
MEMORY_MAX_DOCUMENTS = int(os.getenv("MEMORY_MAX_DOCUMENTS", "5000"))

# Limite máximo de tamanho do banco em MB
# 0 = sem limite
MEMORY_MAX_SIZE_MB = int(os.getenv("MEMORY_MAX_SIZE_MB", "500"))

# Dias para reter documentos em memória (0 = indefinido)
MEMORY_RETENTION_DAYS = int(os.getenv("MEMORY_RETENTION_DAYS", "30"))

# Se False, desativa buscas por memória (acelera execução)
ENABLE_MEMORY_RETRIEVAL = True

# ============================================================
# FEATURE TOGGLES - VALIDAÇÕES E AGENTES
# ============================================================

# Ativar validação de tipos (mypy para Python, tsc para TypeScript)
ENABLE_TYPE_CHECKING = os.getenv("ENABLE_TYPE_CHECKING", "true").lower() == "true"

# Ativar análise estática de código (pylint, flake8, bandit)
ENABLE_STATIC_ANALYSIS = os.getenv("ENABLE_STATIC_ANALYSIS", "true").lower() == "true"

# Ativar execução automática de testes (pytest, unittest, jest)
ENABLE_TEST_EXECUTION = os.getenv("ENABLE_TEST_EXECUTION", "true").lower() == "true"

# Se True, o Reviewer pode refinar o plano se resultado insatisfatório
ENABLE_REFINEMENT_LOOP = os.getenv("ENABLE_REFINEMENT_LOOP", "true").lower() == "true"

# Ativar recuperação automática de erros com análise de root cause
ENABLE_ERROR_RECOVERY = os.getenv("ENABLE_ERROR_RECOVERY", "true").lower() == "true"

# Ativar cache inteligente de snippets bem-sucedidos
ENABLE_CACHE_SNIPPETS = os.getenv("ENABLE_CACHE_SNIPPETS", "true").lower() == "true"

# Ativar aprendizado a partir de padrões de erro anterior
ENABLE_ERROR_LEARNING = os.getenv("ENABLE_ERROR_LEARNING", "true").lower() == "true"

# ============================================================
# CACHE INTELIGENTE DE CÓDIGO
# ============================================================

# Threshold de similaridade para sugerir snippet do cache (0.0-1.0)
# 0.85 = 85% similar (conservador, apenas muito parecidos)
CACHE_REUSE_THRESHOLD = float(os.getenv("CACHE_REUSE_THRESHOLD", "0.85"))

# ============================================================
# CI/CD PIPELINE
# ============================================================

# Ativar pipeline CI/CD como gateway antes do agente executar
CI_CD_ENABLED = os.getenv("CI_CD_ENABLED", "true").lower() == "true"

# Porta para webhook de CI/CD (integração com GitHub Actions, GitLab CI)
CI_CD_WEBHOOK_PORT = int(os.getenv("CI_CD_WEBHOOK_PORT", "5000"))

# Detectar automaticamente pipeline files (.github/workflows, .gitlab-ci.yml)?
CI_CD_AUTO_DETECT = os.getenv("CI_CD_AUTO_DETECT", "true").lower() == "true"

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
# API / AUTENTICAÇÃO
# ============================================================

# Chave de API padrão para autenticação no servidor Continue.dev
# IMPORTANTE: Mude este valor em produção!
DEFAULT_API_KEY = os.getenv("DEFAULT_API_KEY", "dev-api-key-change-in-production")

# Secret key para JWT tokens
# IMPORTANTE: Gere uma chave segura em produção: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-in-production")

# Tempo de expiração do token JWT em horas
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

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
