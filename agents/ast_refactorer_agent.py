"""
============================================================
AST REFACTORER AGENT - Safe Code Transformation
============================================================
Responsável por:
- Transformação AST segura (libcst)
- Adicionar type hints
- Renomear variáveis (snake_case/camelCase)
- Extrair funções complexas
- Simplificar condições
- Refatoração de padrões comuns

Fluxo: Type Checker (detecta problema) → AST Refactorer (corrige) → Type Checker (valida)
============================================================
"""

import ast
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

try:
    import libcst as cst
except ImportError:
    cst = None

from core.config import logger, PROJECT_ROOT
from core.models import TypeCheckResult


class ASTRefactorerAgent:
    """Agent responsável por refatoração segura de código."""
    
    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.project_root = project_root
        self.logger = logger
        
        if cst is None:
            self.logger.warning("libcst não instalado - refactoring limitado")
    
    def add_type_hints(self, file_path: str) -> Tuple[bool, str]:
        """
        Adiciona type hints automaticamente baseado em sugestões.
        
        Args:
            file_path: Arquivo a refatorar
        
        Returns:
            (success, modified_code)
        """
        file_path = Path(file_path)
        if not file_path.is_absolute():
            file_path = self.project_root / file_path
        
        if not file_path.exists():
            return (False, "")
        
        if cst is None:
            return self._add_type_hints_ast(file_path)
        
        return self._add_type_hints_libcst(file_path)
    
    def _add_type_hints_libcst(self, file_path: Path) -> Tuple[bool, str]:
        """Adiciona type hints usando libcst."""
        try:
            with open(file_path) as f:
                source_code = f.read()
            
            module = cst.parse_module(source_code)
            transformer = TypeHintTransformer()
            modified_tree = module.visit(transformer)
            
            return (True, modified_tree.code)
        
        except Exception as e:
            self.logger.error(f"Erro ao adicionar type hints com libcst: {str(e)}")
            return (False, "")
    
    def _add_type_hints_ast(self, file_path: Path) -> Tuple[bool, str]:
        """
        Adiciona type hints simples usando ast (fallback).
        Apenas adiciona "Any" onde falta.
        """
        try:
            with open(file_path) as f:
                source_code = f.read()
            
            tree = ast.parse(source_code)
            
            # Contar funções que precisam de hints
            needs_hints = 0
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.returns is None:
                        needs_hints += 1
            
            if needs_hints == 0:
                return (True, source_code)
            
            # Para fallback simples, retornar código com comentários
            lines = source_code.split("\n")
            modified_lines = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.returns is None:
                        # Adicionar comentário sugerindo type hint
                        modified_lines.append(f"# TODO: Add return type hint for {node.name}")
            
            # Por simplicidade, apenas retornar código original com warning
            self.logger.warning(
                f"Sem libcst, refactoring limitado. "
                f"Install: pip install libcst"
            )
            return (False, source_code)
        
        except Exception as e:
            self.logger.error(f"Erro ao adicionar type hints ast: {str(e)}")
            return (False, "")
    
    def rename_variables(self, file_path: str, style: str = "snake_case") -> Tuple[bool, str]:
        """
        Renomeia variáveis para um estilo específico.
        
        Args:
            file_path: Arquivo a refatorar
            style: "snake_case" ou "camelCase"
        
        Returns:
            (success, modified_code)
        """
        if cst is None:
            self.logger.warning("libcst não disponível")
            return (False, "")
        
        file_path = Path(file_path)
        if not file_path.is_absolute():
            file_path = self.project_root / file_path
        
        try:
            with open(file_path) as f:
                source_code = f.read()
            
            module = cst.parse_module(source_code)
            transformer = VariableRenameTransformer(style)
            modified_tree = module.visit(transformer)
            
            return (True, modified_tree.code)
        
        except Exception as e:
            self.logger.error(f"Erro ao renomear variáveis: {str(e)}")
            return (False, "")
    
    def extract_function(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        func_name: str
    ) -> Tuple[bool, str]:
        """
        Extrai um bloco de código em uma função separada.
        
        Args:
            file_path: Arquivo
            start_line: Linha inicial do bloco
            end_line: Linha final do bloco
            func_name: Nome da nova função
        
        Returns:
            (success, modified_code)
        """
        file_path = Path(file_path)
        if not file_path.is_absolute():
            file_path = self.project_root / file_path
        
        try:
            with open(file_path) as f:
                lines = f.readlines()
            
            if start_line < 1 or end_line > len(lines):
                return (False, "Linhas fora de range")
            
            # Extrair bloco
            block_lines = lines[start_line-1:end_line]
            block_code = "".join(block_lines)
            
            # Criar função
            # Detectar indentação
            indent = len(block_lines[0]) - len(block_lines[0].lstrip())
            indent_str = " " * indent
            
            new_function = f"""
def {func_name}():
{indent_str}    {block_code.lstrip()}
"""
            
            # Substituir bloco original com chamada à função
            modified_lines = (
                lines[:start_line-1] +
                [f"{indent_str}{func_name}()\n"] +
                [new_function] +
                lines[end_line:]
            )
            
            return (True, "".join(modified_lines))
        
        except Exception as e:
            self.logger.error(f"Erro ao extrair função: {str(e)}")
            return (False, "")
    
    def simplify_conditionals(self, file_path: str) -> Tuple[bool, str]:
        """
        Simplifica condições complexas quando possível.
        """
        if cst is None:
            self.logger.warning("libcst não disponível")
            return (False, "")
        
        file_path = Path(file_path)
        if not file_path.is_absolute():
            file_path = self.project_root / file_path
        
        try:
            with open(file_path) as f:
                source_code = f.read()
            
            module = cst.parse_module(source_code)
            transformer = ConditionalSimplifierTransformer()
            modified_tree = module.visit(transformer)
            
            return (True, modified_tree.code)
        
        except Exception as e:
            self.logger.error(f"Erro ao simplificar condicionais: {str(e)}")
            return (False, "")
    
    def remove_unused_imports(self, file_path: str) -> Tuple[bool, str]:
        """Remove imports não utilizadas."""
        if cst is None:
            self.logger.warning("libcst não disponível")
            return (False, "")
        
        file_path = Path(file_path)
        if not file_path.is_absolute():
            file_path = self.project_root / file_path
        
        try:
            with open(file_path) as f:
                source_code = f.read()
            
            # Usar ast para detectar imports não usadas
            tree = ast.parse(source_code)
            
            # Extrair nomes importados
            imported_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_names.add(alias.asname or alias.name)
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        imported_names.add(alias.asname or alias.name)
            
            # Extrair nomes usados
            used_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    used_names.add(node.id)
            
            # Encontrar imports não usadas
            unused = imported_names - used_names
            
            if not unused:
                return (True, source_code)
            
            # Remover imports não usadas com libcst
            module = cst.parse_module(source_code)
            transformer = UnusedImportRemoverTransformer(unused)
            modified_tree = module.visit(transformer)
            
            return (True, modified_tree.code)
        
        except Exception as e:
            self.logger.error(f"Erro ao remover imports: {str(e)}")
            return (False, "")
    
    def apply_refactoring(self, file_path: str, operations: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Aplica múltiplas operações de refactoring em sequência.
        
        Args:
            file_path: Arquivo
            operations: Lista de operações (type, params)
        
        Returns:
            (success, modified_code)
        """
        file_path = Path(file_path)
        
        try:
            with open(file_path) as f:
                code = f.read()
            
            for op in operations:
                op_type = op.get("type")
                
                if op_type == "add_type_hints":
                    success, code = self.add_type_hints(str(file_path))
                    if not success:
                        return (False, code)
                
                elif op_type == "remove_unused_imports":
                    success, code = self.remove_unused_imports(str(file_path))
                    if not success:
                        return (False, code)
                
                elif op_type == "simplify_conditionals":
                    success, code = self.simplify_conditionals(str(file_path))
                    if not success:
                        return (False, code)
            
            return (True, code)
        
        except Exception as e:
            self.logger.error(f"Erro ao aplicar refactorings: {str(e)}")
            return (False, "")


# ============================================================
# LIBCST TRANSFORMERS
# ============================================================

class TypeHintTransformer(cst.CSTTransformer):
    """Adiciona type hints automaticamente."""
    
    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> cst.FunctionDef:
        """Adiciona return type hint se não existir."""
        if original_node.returns is None:
            # Adicionar Any como fallback
            new_node = original_node.with_changes(
                returns=cst.Annotation(annotation=cst.Name("Any"))
            )
            return new_node
        return original_node


class VariableRenameTransformer(cst.CSTTransformer):
    """Renomeia variáveis para um estilo específico."""
    
    def __init__(self, style: str = "snake_case"):
        self.style = style
        self.renames = {}
    
    def leave_Name(self, original_node: cst.Name) -> cst.Name:
        """Renomeia nomes de variáveis."""
        name = original_node.value
        
        if name not in self.renames:
            if self.style == "snake_case":
                self.renames[name] = self._to_snake_case(name)
            elif self.style == "camelCase":
                self.renames[name] = self._to_camel_case(name)
        
        new_name = self.renames.get(name, name)
        return original_node.with_changes(value=new_name)
    
    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Converte para snake_case."""
        s1 = "".join(["_" + c if c.isupper() else c for c in name])
        return s1.lower().lstrip("_")
    
    @staticmethod
    def _to_camel_case(name: str) -> str:
        """Converte para camelCase."""
        parts = name.split("_")
        return parts[0] + "".join(p.capitalize() for p in parts[1:])


class ConditionalSimplifierTransformer(cst.CSTTransformer):
    """Simplifica condições complexas."""
    
    pass  # Implementação complexa - deixar para v2


class UnusedImportRemoverTransformer(cst.CSTTransformer):
    """Remove imports não usadas."""
    
    def __init__(self, unused_names: set):
        self.unused_names = unused_names
    
    def leave_ImportFrom(self, original_node: cst.ImportFrom) -> cst.RemovalSentinel | cst.ImportFrom:
        """Remove ImportFrom com imports não usadas."""
        if isinstance(original_node.names, cst.ImportStar):
            return original_node
        
        # Filter imports
        new_names = []
        for name in original_node.names:
            if isinstance(name, cst.ImportAlias):
                imported_name = name.asname.name.value if name.asname else name.name.value
                if imported_name not in self.unused_names:
                    new_names.append(name)
        
        if not new_names:
            return cst.RemovalSentinel.REMOVE
        
        return original_node.with_changes(names=new_names)
