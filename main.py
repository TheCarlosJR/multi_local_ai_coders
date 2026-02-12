"""
============================================================
AGENTE IA AUTÔNOMO LOCAL
============================================================
Ponto de entrada para execução do agente.

Uso:
  python main.py
  python main.py "seu objetivo aqui"
"""

import sys
import json
from pathlib import Path

from core.agent_runner import run
from core.config import logger


def print_header():
    """Imprime cabeçalho do agente."""
    
    header = """
╔══════════════════════════════════════════════════════════════╗
║                   AI AUTONOMOUS AGENT v1.0                   ║
║              Local LLM Powered (Ollama + Qwen)               ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(header)


def print_result(result: dict):
    """Formata e imprime resultado da execução."""
    
    success = result.get("success", False)
    
    print("\n" + "=" * 60)
    
    if success:
        print("✓ SUCESSO!")
        print(f"\nResultado:\n{result.get('result', 'N/A')}")
        
        review = result.get("review", {})
        if review:
            print(f"\nConfiança da revisão: {review.get('confidence', 0):.2%}")
            summary = review.get("summary", "")
            if summary:
                print(f"Resumo: {summary}")
    else:
        print("✗ FALHOU")
        error = result.get("error", "Erro desconhecido")
        print(f"\nErro: {error}")
        
        issues = result.get("issues", [])
        if issues:
            print(f"\nProblemas encontrados:")
            for issue in issues:
                print(f"  - {issue.get('issue', 'N/A')} "
                      f"[{issue.get('severity', 'medium')}]")
    
    print("=" * 60)


def save_result_json(result: dict, output_file: str = "result.json"):
    """Salva resultado em JSON para processamento posterior."""
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n✓ Resultado salvo em: {output_file}")
    except Exception as e:
        logger.warning(f"Não conseguiu salvar em JSON: {e}")


def main():
    """Função principal."""
    
    print_header()
    
    # Obter objetivo
    if len(sys.argv) > 1:
        # Objetivo passou como argumento
        goal = " ".join(sys.argv[1:])
        print(f"Objetivo: {goal}\n")
    else:
        # Pedir ao usuário
        print("Defina o objetivo para o agente:")
        print("(Exemplos: 'Crie um arquivo hello.py', 'Verifique a ramificação git')\n")
        goal = input("Objetivo: ").strip()
        
        if not goal:
            print("✗ Nenhum objetivo definido")
            return 1
    
    # Executar agente
    print("\n[Iniciando execução...]\n")
    
    try:
        result = run(goal)
        
        # Exibir resultado
        print_result(result)
        
        # Salvar JSON
        save_result_json(result)
        
        # Retornar código apropriado
        return 0 if result.get("success") else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠ Execução cancelada pelo usuário")
        return 2
    except Exception as e:
        logger.error(f"Erro não esperado: {e}", exc_info=True)
        print(f"\n✗ Erro inesperado: {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())

