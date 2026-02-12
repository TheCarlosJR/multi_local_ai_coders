# Sistema de agentes inteligentes

## Objetivo

Agente autônomo real que planeja, executa, revisa, usa git, terminal, web, utiliza multi-agentes com o objetivo de auxiliar projetos de desenvolvimento de software utilizando Continue (para utilizar no vscode), Ollama e um modelo em execução local

## Ciclo cognitivo

Recebe objetivo
↓
Planeja
↓
Pergunta dúvidas (se necessário)
↓
Refina plano
↓
Executa passo a passo
↓
Avalia resultado
↓
Itera até concluir

## Tecnologias Principais

| Component | Purpose |
|-----------|---------|
| Ollama | Modelos LLM local (ex.: qwen2.5-coder, granite, etc.) |
| Python | Orquestrador principal |
| AutoGen (Microsoft) | Framework multi-agente coordenado em Python |
| LangChain / LangGraph | Fluxos, agentes com tools e memória |
| ChromaDB (ou similar) | Vector store para RAG (memória de contexto) |
| PydanticAI / CreateAgents | Saída estruturada e segurança em tasks |
| Tools personalizadas | Arquivos, terminal, Git, web scraping/automações |
| Continue / VSCode integration | UI de interação e edição |

## Principais Agentes

### 🧭 Planner Agent

* Recebe uma meta complexa.

* Gera um plano estruturado (JSON).

* Divide em subtarefas.

### 🛠 Executor Agent

* Interpreta e executa subtarefas.

* Pode chamar tools (terminal, web, git, fs).

### 🔍 Reviewer/Critic Agent

* Analisa execução.

* Verifica erros, test failures, logs.

* Solicita correções ao Planner.

### 🧠 Memory Agent

* Armazena contexto em vetor (RAG) para:

- commits prévios,

- histórico de chats,

- arquivos relevantes.