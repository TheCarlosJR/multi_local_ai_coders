"""
QUICKSTART - Guia de Início Rápido

Execute este script para configurar e testar o agente.
"""

import subprocess
import sys
import os
from pathlib import Path


def print_step(step_num, title, description=""):
    """Imprime um step formatado."""
    print(f"\n{'='*60}")
    print(f"[STEP {step_num}] {title}")
    if description:
        print(f"    {description}")
    print('='*60)


def run_command(cmd, check=True):
    """Executa comando e retorna sucesso/erro."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if check and result.returncode != 0:
            print(f"✗ Erro: {result.stderr}")
            return False
        print(f"✓ Sucesso")
        return True
    except Exception as e:
        print(f"✗ Erro ao executar: {e}")
        return False


def main():
    print("\n" + "╔" + "="*58 + "╗")
    print("║" + " "*15 + "QUICKSTART - AI AGENT SETUP" + " "*15 + "║")
    print("╚" + "="*58 + "╝")
    
    # ============================================================
    # STEP 1: Verificar Python
    # ============================================================
    print_step(1, "Verificando Python", "Versão 3.8+")
    
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"Python {version} ✓")
    
    if sys.version_info < (3, 8):
        print("✗ Python 3.8+ necessário")
        return 1
    
    # ============================================================
    # STEP 2: Instalar dependências
    # ============================================================
    print_step(2, "Instalando dependências", "pip install -r docs/requirements.txt")
    
    if not run_command("pip install -r docs/requirements.txt"):
        print("\n⚠️  Alguns pacotes podem não ter instalado")
        print("   Instalando manualmente...")
        packages = [
            "ollama",
            "pydantic>=2.0",
            "python-dotenv",
            "GitPython",
            "requests",
            "beautifulsoup4",
            "chromadb",
            "sentence-transformers",
        ]
        for pkg in packages:
            print(f"  - Instalando {pkg}...")
            run_command(f"pip install {pkg}", check=False)
    
    # ============================================================
    # STEP 3: Verificar Ollama
    # ============================================================
    print_step(3, "Verificando Ollama", "http://localhost:11434")
    
    try:
        import ollama
        models = ollama.list()
        print(f"✓ Ollama respondendo")
        
        if models:
            print(f"\nModelos disponíveis:")
            for model in models.get("models", []):
                name = model.get("name", "unknown")
                print(f"  - {name}")
        else:
            print("⚠️  Nenhum modelo em Ollama")
            print("\nPasse 1: Puxar modelo recomendado (opcional)")
            print("  ollama pull qwen-coder-2.5")
            print("  ou")
            print("  ollama pull qwen:14b")
    except ImportError:
        print("✗ ollama não está instalado. Execute: pip install ollama")
        return 1
    except Exception as e:
        print(f"✗ Erro ao conectar: {e}")
        print("\n  Ollama não está respondendo")
        print("  Certifique-se de que está rodando: ollama serve")
        return 1
    
    # ============================================================
    # STEP 4: Verificar .env
    # ============================================================
    print_step(4, "Verificando configuração", ".env")
    
    if Path(".env").exists():
        print("✓ .env encontrado")
        
        import os
        from dotenv import load_dotenv
        load_dotenv()
        model = os.getenv("OLLAMA_MODEL", "não configurado")
        print(f"  Modelo configurado: {model}")
    else:
        print("⚠️  .env não encontrado")
        print("  Copiando .env.example → .env")
        if Path(".env.example").exists():
            import shutil
            shutil.copy(".env.example", ".env")
            print("✓ .env criado")
        else:
            print("✗ .env.example não encontrado")
            return 1
    
    # ============================================================
    # STEP 5: Teste simples
    # ============================================================
    print_step(5, "Testando sistema", "Import dos módulos")
    
    try:
        print("  - Importando core...")
        from core import config, llm, models
        print("    ✓ core OK")
        
        print("  - Importando agents...")
        from agents import planner, executor, reviewer, memory
        print("    ✓ agents OK")
        
        print("  - Importando tools...")
        from tools import filesystem_tool, terminal_tool, git_tool, web_tool
        print("    ✓ tools OK")
        
        print("\n✓ Todos os módulos importados com sucesso!")
        
    except ImportError as e:
        print(f"✗ Erro de import: {e}")
        return 1
    except Exception as e:
        print(f"✗ Erro: {e}")
        return 1
    
    # ============================================================
    # CONCLUSÃO
    # ============================================================
    print("\n" + "="*60)
    print("✓ SETUP CONCLUÍDO COM SUCESSO!")
    print("="*60)
    
    print("\n📝 Próximos passos:")
    print("  1. Configure OLLAMA_MODEL em .env para qwen-coder-2.5 (opcional)")
    print("  2. Execute: python main.py")
    print("  3. Ou: python main.py 'seu objetivo aqui'")
    print("\n💡 Exemplos de objetivos:")
    print("  - 'Crie um arquivo hello.py que imprime Hello World'")
    print("  - 'Mostre o status do repositório git'")
    print("  - 'Crie um arquivo requirements.txt com dependências do projeto'")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
