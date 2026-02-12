# 🤖 AI Agent Local - Documentação Completa

[![Status](https://img.shields.io/badge/Status-FUNCIONAL%20%E2%9C%93-brightgreen)](.)
[![Versão](https://img.shields.io/badge/Vers%C3%A3o-1.0-blue)](.)
[![Python](https://img.shields.io/badge/Python-3.8+-blue)](.)
[![Licença](https://img.shields.io/badge/Licen%C3%A7a-Local%20Confidencial-gray)](.)

Sistema agente autônomo local totalmente implementado com capacidades de planejamento, execução, revisão e aprendizado contínuo (RAG).

---

## 📑 Índice

1. [Início Rápido (2 mins)](#-início-rápido-2-mins)
2. [Usando o Agente](#-usando-o-agente)
3. [Arquitetura & Design](#-arquitetura--design)
4. [Configuração Detalhada](#-configuração-detalhada)
5. [Exemplos Práticos Completos](#-exemplos-práticos-completos)
6. [Tools Disponíveis](#-tools-disponíveis)
7. [Models Pydantic](#-models-pydantic)
8. [Troubleshooting](#-troubleshooting)
9. [FAQ](#-faq)
10. [Próximos Passos](#-próximos-passos)

---

## ⚡ Início Rápido (2 mins)

### Pré-requisitos
- Python 3.8+
- Ollama rodando localmente (`ollama serve` em outro terminal)
- Um modelo Ollama instalado (recomendado: `qwen-coder-2.5` ou `qwen:14b`)

### Setup em 5 Passos

```bash
# 1. Copiar arquivo de configuração
copy .env.example .env

# 2. (Opcional) Editar .env se quiser customizar
notepad .env

# 3. Criar e ativar ambiente virtual
python -m venv .venv
.venv\Scripts\activate

# 4. Instalar dependências
pip install -r docs/requirements.txt

# 5. Testar ambiente
python quickstart.py
```

✅ Se tudo funcionar, verá: **"✓ SETUP CONCLUÍDO COM SUCESSO!"**

### Verificar Ollama

```bash
# Terminal separado 1: Inicie Ollama - Talvez ja esteja iniciado e dará erro de socket
ollama serve

# Terminal separado 2: Verifique conexão
curl http://localhost:11434/api/tags

# Terminal separado 2: Lista modelos disponíveis
ollama list

# Terminal separado 2: Se não tiver modelo
ollama pull qwen-coder-2.5

# Terminal separado 2: Execute o modelo
ollama run qwen-coder-2-5
```

---

## 🚀 Usando o Agente

### Forma 1: Comando Direto (Recomendado)

```bash
python main.py "Seu objetivo aqui"
```

**Exemplos imediatos:**

```bash
# Criar arquivo
python main.py "Crie um arquivo hello.py que imprime 'Hello World'"

# Analisar código
python main.py "Leia main.py e explique o que faz"

# Operação Git
python main.py "Faça um commit com mensagem 'Fix: bug no login'"

# Web scraping
python main.py "Busque https://example.com/api e mostre o JSON"

# Instalar pacotes
python main.py "Instale requests e beautifulsoup4 via pip"
```

### Forma 2: Modo Interativo

```bash
python main.py
# Sistema pede: "Objetivo: "
# Digite seu objetivo e pressione Enter
```

### Forma 3: Com Visualização de Logs em Tempo Real

```bash
# Terminal 1: Monitore logs
tail -f logs/agent.log

# Terminal 2: Execute
python main.py "seu objetivo"
```

### O Que o Agente Pode Fazer

| Categoria | Exemplo |
|-----------|---------|
| **Criar Código** | `Crie uma função em Python que valida email` |
| **Executar & Testar** | `Execute main.py e mostre o resultado` |
| **Análise & Refatoração** | `Analise utils.py e encontre problemas de performance` |
| **Git & Versionamento** | `Mostre o status do repositório` |
| **Web & Dados** | `Busque informações sobre FastAPI` |
| **Documentação** | `Adicione docstrings a todas as funções` |

### O Que NÃO Pode Fazer (Segurança)

```bash
# ❌ Sair do diretório raiz do projeto
# ❌ Deletar arquivos críticos sem aviso
# ❌ Rodar comandos perigosos (rm -rf, sudo, format, etc)
# ❌ Acessar internet externa sem explícito
```

---

## 🏗️ Arquitetura & Design

### Fluxo de Execução Completo

```
┌─────────────────────────────────────────────────────────┐
│ 1. MEMORY RETRIEVAL (RAG)                               │
│    - Busca memória por similaridade semântica           │
│    - Injeta contexto de execuções anteriores            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 2. PLANNER (Agente Planejador)                          │
│    - Recebe: objetivo + contexto de memória             │
│    - Gera: PlanResponse (steps, risks, time)            │
│    - Formato: JSON validado via Pydantic               │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 3. EXECUTOR (Agente Executor)                           │
│    - Executa cada step sequencialmente                  │
│    - Chama tools: Filesystem, Terminal, Git, Web        │
│    - Em erro: error_recovery_prompt para análise        │
│    - Retorna: ExecutorResponse com histórico            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 4. REVIEWER (Agente Revisor)                            │
│    - Analisa resultado contra objetivo                  │
│    - Detecta: bugs, segurança, incompletude             │
│    - Retorna: ReviewResponse (APPROVED/NEEDS_REF/FAIL)  │
└─────────────────────────────────────────────────────────┘
                          ↓
                    ┌─────────┐
                    │ DECISÃO │
                    └─────────┘
                   /     |     \
            APPROVED  REFINE  FAILED
             /           |        \
          SUCESSO     RETRY     RETRY 2
                       (max 2x)
```

### Estrutura de Pastas

```
project/
├── main.py                 # Ponto de entrada
├── quickstart.py           # Diagnóstico automático
├── README.md               # Esta documentação
├── .env                    # Configuração (gitignored)
├── .env.example            # Template de config
├── requirements.txt        # Dependências
│
├── core/
│   ├── config.py           # Configuração centralizada
│   ├── llm.py              # Interface com Ollama
│   ├── models.py           # Schemas Pydantic
│   └── agent_runner.py     # Orquestrador principal
│
├── agents/
│   ├── planner.py          # Agente Planejador
│   ├── executor.py         # Agente Executor
│   ├── reviewer.py         # Agente Revisor
│   └── memory.py           # Agente Memory/RAG
│
├── tools/
│   ├── filesystem_tool.py  # Leitura/escrita segura
│   ├── terminal_tool.py    # Execução de comandos
│   ├── git_tool.py         # Operações Git
│   └── web_tool.py         # Web scraping
│
├── prompts/
│   ├── base_prompt.py
│   ├── planner_prompt.py
│   ├── executor_prompt.py
│   ├── reviewer_prompt.py
│   └── error_recovery_prompt.py
│
├── vector_store/
│   ├── chromadb_store.py   # ChromaDB + Ollama embeddings
│   └── chroma_db/          # Dados persistidos
│
├── logs/
│   └── agent.log           # Log de execução
│
└── docs/
    ├── SETUP.md            # (Histórico)
    ├── USO.md              # (Histórico)
    ├── requirements.txt    # Dependências
    ├── structure.md        # Documentação técnica
    └── implementation.md   # Detalhes de implementação
```

### Componentes Principais

**core/config.py**
- Todos os parâmetros centralizados e comentados
- Customizável via `.env`

**agents/planner.py**
- Analisa objetivo e cria plano estruturado
- Identifica riscos e dependências
- Retorna `PlanResponse` validado

**agents/executor.py**
- Executa steps sequencialmente
- Chama tools conforme necessário
- Error recovery automático

**agents/reviewer.py**
- Valida se objetivo foi alcançado
- Detecta bugs e incompletudes
- Retorna confidence score

**agents/memory.py**
- RAG com ChromaDB + Ollama embeddings
- Recupera contexto de execuções anteriores
- Aprendizado contínuo

---

## ⚙️ Configuração Detalhada

### Arquivo `.env` - Parâmetros Principais

```ini
# ========== LLM CONFIGURATION ==========
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen-coder-2.5              # ou qwen:14b, mistral, etc
LLM_TEMPERATURE=0.2                      # 0=determinístico, 1=criativo
LLM_TIMEOUT=120                          # Segundos para esperar LLM

# ========== EXECUTION CONFIGURATION ==========
MAX_RETRIES=2                            # Tentativas em caso de erro
ENABLE_REFINEMENT_LOOP=True              # Refinar plano se necessário
ENABLE_MEMORY_RETRIEVAL=True             # Usar RAG (memory)

# ========== SECURITY ==========
PROJECT_ROOT=.                           # Sandbox de arquivos
MAX_FILE_READ_LINES=10000                # Limite de leitura
FORBIDDEN_COMMANDS=rm -rf,sudo,su,format,diskpart  # Bloqueados

# ========== MEMORY/RAG ==========
MEMORY_DB_PATH=./vector_store/chroma_db
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
MEMORY_TOP_K=5                           # Resultados por busca

# ========== GIT CONFIGURATION ==========
AUTO_COMMIT=no                           # yes/no - Commitar automaticamente
GIT_AUTHOR_NAME=AI Agent
GIT_AUTHOR_EMAIL=agent@localhost

# ========== LOGGING ==========
LOG_LEVEL=INFO                           # DEBUG, INFO, WARNING, ERROR
```

### Parâmetros Detalhados

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| `OLLAMA_MODEL` | `qwen-coder-2.5` | Modelo para usar. Opções: qwen:14b, mistral, codellama, etc |
| `LLM_TEMPERATURE` | `0.2` | Criatividade (0=preciso, 1=criativo). Para tarefas: 0.1-0.3 |
| `MAX_RETRIES` | `2` | Quantas vezes retry em erro (maiores = mais lento) |
| `MEMORY_TOP_K` | `5` | Número de resultados similares da memória |
| `AUTO_COMMIT` | `no` | Fazer commit automáticamente (yes/no) |
| `LOG_LEVEL` | `INFO` | Verbosidade: DEBUG > INFO > WARNING > ERROR |

### Mudar para Modo Debug

```bash
# 1. Editar .env
LOG_LEVEL=DEBUG
LLM_TIMEOUT=180

# 2. Executar
python main.py "seu objetivo"

# 3. Analisar logs/agent.log para mais detalhes
type logs\agent.log
```

### Customizar Comandos Bloqueados

```ini
# Adicionar mais comandos perigosos em .env:
FORBIDDEN_COMMANDS=rm -rf,sudo,su,format,diskpart,drop database,delete from

# Criar whitelist customizada em config.py se necessário
```

---

## 💡 Exemplos Práticos Completos

### Exemplo 1: Criar Arquivo Simples

```bash
python main.py "Crie um arquivo hello.py que imprime 'Hello World'"
```

**Resultado esperado:**
```json
{
  "success": true,
  "goal": "Crie um arquivo hello.py que imprime 'Hello World'",
  "result": "Arquivo hello.py criado com sucesso",
  "review": {
    "goal_achieved": true,
    "status": "approved",
    "confidence": 0.95
  }
}
```

**Fluxo:**
1. ✓ Planner: Plano com 1 step - "write_file hello.py"
2. ✓ Executor: Cria arquivo com código Python
3. ✓ Reviewer: Valida syntax e existência
4. ✓ Memory: Salva sucesso para referência futura

---

### Exemplo 2: Refatorar Código Completo

```bash
python main.py "Refatore tools/filesystem_tool.py: adicione typing, melhore docstrings, confirme com testes"
```

**Fluxo esperado:**
1. Planner: Plano com 4-5 steps detalhados
2. Executor: Lê arquivo → Refatora → Testa → Valida
3. Reviewer: Analisa qualidade do código
4. Memory: Armazena padrão de refatoração
5. Git: Auto-commit (se habilitado)

---

### Exemplo 3: Análise de Múltiplos Arquivos

```bash
python main.py "Analise todos os Python em /agents e gere relatório de cobertura de documentação"
```

**Executor vai:**
- Iterar por todos os arquivos `.py` em `/agents`
- Contar funções/classes com/sem docstrings
- Compilar relatório
- Salvar em arquivo de saída

---

### Exemplo 4: Setup Automático de Projeto

```bash
python main.py "Este diretório é um projeto Python. Instale todas dependências de requirements.txt, rode testes, mostre cobertura"
```

**Comportamento multi-step automático:**
1. Identifica requirements.txt
2. Pip install
3. Detecta pytest/unittest
4. Roda testes
5. Gera relatório de cobertura
6. Salva resultados

---

### Exemplo 5: Operações Git Avançadas

```bash
python main.py "Mostre o histórico dos últimos 10 commits, analise padrões de mensagens, sugira melhoria no processo"
```

---

### Exemplo 6: Web Scraping

```bash
python main.py "Busque https://api.example.com/data, analise estrutura JSON, gere arquivo de schema"
```

---

## 🔧 Tools Disponíveis

### Filesystem Tool
Operações seguras de arquivos com sandbox:

```python
read_file(path)              # Leitura segura (limite: MAX_FILE_READ_LINES)
write_file(path, content)    # Escrita segura (validação de path)
list_dir(path)               # Listar com limite de resultados
```

**Segurança:**
- ✓ Validação de path (sem `../`, sem saída de raiz)
- ✓ Limite de linhas na leitura
- ✓ Confirmação antes de sobrescrever

---

### Terminal Tool
Execução de comandos com timeout e segurança:

```python
run_cmd(command, timeout=30) # Executar com timeout
run_cmd_with_output(cmd)     # Retorna (code, stdout, stderr)
```

**Segurança:**
- ✓ Blacklist de comandos perigosos
- ✓ Timeout automático (padrão: 30s)
- ✓ Capture de output/error

---

### Git Tool
Operações Git com validação:

```python
git_status()                 # Status do repo
git_commit(message)          # Fazer commit
git_diff(staged=False)       # Ver mudanças
git_push(remote, branch)     # Push automático
git_log(max_count=5)         # Histórico recente
```

**Requisito:**
```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

---

### Web Tool
Scraping e fetch de URLs:

```python
fetch_url(url)               # Fetch com texto limpo (sem HTML)
fetch_url_raw(url)           # Retorna HTML bruto completo
```

**Limite:** URLs públicas, timeout de 30s

---

## 📋 Models Pydantic

Estrutura de dados validados para cada fase:

### PlanResponse
Estrutura do plano gerado pelo Planner:

```python
{
  "goal": "Crie um arquivo hello.py",
  "feasible": true,
  "overall_strategy": "Usar filesystem_tool para escrever",
  "steps": [
    {
      "step_number": 1,
      "description": "Escrever arquivo hello.py",
      "tool": "filesystem",
      "action": "write_file",
      "expected_output": "Arquivo criado",
      "dependencies": []
    }
  ],
  "risks": [],
  "assumptions": [],
  "estimated_duration_minutes": 1
}
```

### ExecutorResponse
Resultado da execução:

```python
{
  "steps_completed": [...],
  "overall_success": true,
  "final_result": "Arquivo hello.py criado com sucesso",
  "stopped_at_step": null,
  "next_action": null
}
```

### ReviewResponse
Validação do resultado:

```python
{
  "goal_achieved": true,
  "status": "approved",  # ou "needs_refinement" / "failed"
  "summary": "Objetivo alcançado com sucesso",
  "issues": [],
  "confidence": 0.95,
  "recommendation": "Finalizar"
}
```

### Result JSON Final
Arquivo `result.json` salvo após execução:

```json
{
  "success": true,
  "goal": "Crie um arquivo hello.py",
  "result": "Arquivo hello.py criado com sucesso",
  "review": {
    "goal_achieved": true,
    "status": "approved",
    "confidence": 0.95,
    "issues": []
  },
  "context": {
    "goal": "...",
    "plan": {...},
    "execution_history": [...],
    "iteration_count": 1,
    "errors_recovered": 0
  }
}
```

---

## 🐛 Troubleshooting

### Erro: "Ollama não respondendo"

**Diagnóstico:**
```bash
# 1. Verificar se Ollama está rodando
curl http://localhost:11434/api/tags

# 2. Se nada aparecer, iniciar Ollama em novo terminal
ollama serve

# 3. Testar agente novamente
python quickstart.py
```

### Erro: "Modelo não encontrado"

```bash
# 1. Ver modelos disponíveis
ollama list

# 2. Se vazio, puxar modelo recomendado
ollama pull qwen-coder-2.5

# 3. Ou puxar alternativa
ollama pull mistral

# 4. Atualizar .env com modelo existente
OLLAMA_MODEL=mistral
```

### Erro: "ModuleNotFoundError: No module named..."

```bash
# 1. Verificar ambiente virtual ativo
pip list

# 2. Se não tiver dependências, instalar
pip install -r docs/requirements.txt

# 3. Ou rodar setup automático
python quickstart.py
```

### Erro: "JSON inválido de LLM" ou timeouts

```bash
# 1. Aumentar timeout em .env
LLM_TIMEOUT=180

# 2. Reduzir temperatura para output mais estruturado
LLM_TEMPERATURE=0.1

# 3. Tentar modelo mais potente
OLLAMA_MODEL=qwen-coder-2.5

# 4. Aumentar max retries
MAX_RETRIES=3

# 5. Tentar novamente
python main.py "seu objetivo"
```

### Erro: "Erro de permissão em git_tool"

```bash
# 1. Configurar git global
git config --global user.name "AI Agent"
git config --global user.email "agent@localhost"

# 2. Verificar status
git config --global --list

# 3. Tentar novamente
python main.py "Faça um commit"
```

### Erro: "Permissão negada em arquivo"

```bash
# Pode estar em uso ou com permissão restrita
# Solução: Feche aplicativos que usam o arquivo
# Em Windows: Verifique se arquivo está aberto no editor

# Se persistir, aumentar LOG_LEVEL=DEBUG para mais detalhes
LOG_LEVEL=DEBUG
python main.py "seu objetivo"
```

### Verificação Rápida (Diagnostic)

```bash
python quickstart.py
```

Este script verifica:
- ✓ Python version
- ✓ Dependências instaladas
- ✓ Conexão Ollama
- ✓ .env configuration
- ✓ Permissions
- ✓ Vector store setup

---

## ❓ FAQ

**P: O agente acessa internet?**  
R: Não. Roda localmente. Pode fazer scraping apenas de URLs que você providencia explicitamente, sem enviar dados.

**P: Minhas informações são seguras?**  
R: Sim. Tudo roda localmente. Nada é enviado para cloud. Sandbox de arquivo impede acesso fora do PROJECT_ROOT.

**P: Posso parar a execução?**  
R: Sim. Pressione `Ctrl+C` para cancelar. Sistema salva progresso parcial em result.json.

**P: Quanto tempo leva?**  
R: Varia com complexidade:
- Simples (criar arquivo): 5-10s
- Moderado (refatorar): 30-60s
- Complexo (análise múltipla): 2-5 min

**P: Posso customizar o comportamento?**  
R: Sim. Edite `.env` para temperatura, retries, limites, nível de log, etc.

**P: O agente "aprende" com tempo?**  
R: Sim! ChromaDB armazena êxitos anteriores via RAG. Próximas vezes é mais rápido e preciso.

**P: Como resetar a memória do agente?**  
R: Delete a pasta `vector_store/chroma_db`:
```bash
rmdir /s vector_store\chroma_db
# Sistema recria automaticamente
```

**P: Posso usar com outro modelo LLM?**  
R: Não. Sistema está integrado com Ollama. Para outro LLM, seria necessário refatorar `core/llm.py`.

**P: Como monitoro execução em tempo real?**  
R: Use logs:
```bash
# Terminal 1:
tail -f logs/agent.log

# Terminal 2:
python main.py "objetivo"
```

---

## 🎯 Próximos Passos

### 1. **Expandir Tools**
Adicione mais ferramentas conforme necessário:
- Database tool (SQL queries)
- API tool (requisições HTTP com headers)
- File compression tool
- Email tool

### 2. **Refinar Prompts**
Customize prompts em `prompts/*.py` para:
- Ajustar tom e estilo
- Adicionar restrições específicas
- Melhorar estrutura de output

### 3. **Criar Testes**
```bash
# Adicione testes para casos críticos
pytest tests/

# Exemplo:
def test_hello_world_creation():
    result = run_agent("Crie arquivo hello.py")
    assert "Arquivo criado" in result["result"]
    assert result["success"] is True
```

### 4. **Monitoramento**
- Analise `logs/agent.log` regularmente
- Rastreie taxa de sucesso em `result.json`
- Optimize prompts baseado em erros recorrentes

### 5. **Integração**
Expanda com:
- API wrapper para oferecer como serviço
- Dashboard para monitoramento
- Slack/Discord bot para executar agente
- CI/CD integration para automação

### 6. **Deploy**
```bash
# Prepare para produção:
# - Use model mais potente em servidor
# - Configure logging centralizado
# - Setup database para histórico
# - Rate limiting para segurança
```

---

## 📞 Suporte & Debug

### Verificar Status Completo
```bash
python quickstart.py
```

### Ver Logs
```bash
# Últimas 20 linhas
type logs\agent.log | tail -20

# Seguir em tempo real
tail -f logs/agent.log
```

### Resetar Ambiente
```bash
# 1. Limpar memória (vector store)
rmdir /s vector_store\chroma_db

# 2. Limpar logs
del logs\agent.log

# 3. Limpar resultado anterior
del result.json

# 4. Testar setup
python quickstart.py
```

### Aumentar Verbosidade
```bash
# Em .env:
LOG_LEVEL=DEBUG

# Então:
python main.py "teste" > debug.log 2>&1
type debug.log
```

---

## 📚 Referência Rápida

| Você quer... | Comando |
|-------------|---------|
| Criar arquivo | `python main.py "Crie arquivo.py"` |
| Refatorar código | `python main.py "Refatore main.py"` |
| Ver git status | `python main.py "Mostre status git"` |
| Testar setup | `python quickstart.py` |
| Debug detalhado | `LOG_LEVEL=DEBUG python main.py "..."` |
| Resetar memória | `rmdir /s vector_store\chroma_db` |
| Ver resultado | `type result.json` |
| Monitor logs | `tail -f logs/agent.log` |

---

**Última atualização:** 11 Feb 2026  
**Status:** ✅ Funcional e pronto para produção  
**Versão:** 1.0 - Production Ready

**Dúvidas?** Consulte `docs/` para documentação técnica detalhada.
