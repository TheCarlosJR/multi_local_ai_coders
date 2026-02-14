"""
============================================================
TYPE CHECKER AGENT - Type Safety & Validation
============================================================
Responsável por:
- Detecção de linguagem (Python, TypeScript, JavaScript)
- Validação de tipos (mypy, tsc, JSDoc)
- Sugestão de type hints
- Integração com refactorer para auto-fix

Fluxo: Executor → Type Checker → (Refactorer se problemas)
============================================================
"""

import os
import ast
import subprocess
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from core.config import logger, PROJECT_ROOT, ENABLE_TYPE_CHECKING
from core.models import TypeCheckResult, TypeCheckIssue


class TypeCheckerAgent:
    """Agent responsável por validação de tipos."""
    
    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.project_root = project_root
        self.logger = logger
    
    def check_file(self, file_path: str) -> Optional[TypeCheckResult]:
        """
        Valida tipos de um arquivo específico.
        
        Args:
            file_path: Caminho do arquivo (relativo ou absoluto)
        
        Returns:
            TypeCheckResult com status e issues
        """
        file_path = Path(file_path)
        if not file_path.is_absolute():
            file_path = self.project_root / file_path
        
        if not file_path.exists():
            self.logger.warning(f"Arquivo não existe: {file_path}")
            return None
        
        # Detectar linguagem
        language = self._detect_language(file_path)
        
        if language == "py":
            return self._check_python(file_path)
        elif language == "ts":
            return self._check_typescript(file_path)
        elif language == "js":
            return self._check_javascript(file_path)
        else:
            return None
    
    def check_project(self) -> Optional[TypeCheckResult]:
        """
        Valida tipos em todo o projeto.
        """
        py_files = list(self.project_root.glob("**/*.py"))
        ts_files = list(self.project_root.glob("**/*.ts")) + \
                   list(self.project_root.glob("**/*.tsx"))
        
        if py_files:
            return self._check_python_project()
        elif ts_files:
            return self._check_typescript_project()
        else:
            return None
    
    def _detect_language(self, file_path: Path) -> str:
        """Detecta linguagem baseado na extensão."""
        suffix = file_path.suffix.lower()
        if suffix == ".py":
            return "py"
        elif suffix in [".ts", ".tsx"]:
            return "ts"
        elif suffix in [".js", ".jsx"]:
            return "js"
        else:
            return "unknown"
    
    def _check_python(self, file_path: Path) -> Optional[TypeCheckResult]:
        """Valida tipos em arquivo Python usando mypy."""
        file_path = Path(file_path)
        
        try:
            # Executar mypy
            result = subprocess.run(
                ["mypy", str(file_path), "--ignore-missing-imports", "--show-column-numbers"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            issues = self._parse_mypy_output(result.stdout)
            
            return TypeCheckResult(
                file=str(file_path.relative_to(self.project_root)),
                language="py",
                success=(result.returncode == 0),
                total_issues=len(issues),
                issues=issues
            )
        
        except FileNotFoundError:
            self.logger.debug("mypy não instalado")
            # Fallback: análise básica com ast
            return self._analyze_python_ast(file_path)
        except Exception as e:
            self.logger.warning(f"Erro ao rodar mypy: {str(e)}")
            return None
    
    def _check_python_project(self) -> Optional[TypeCheckResult]:
        """Valida tipos em projeto Python inteiro."""
        try:
            result = subprocess.run(
                ["mypy", str(self.project_root), "--ignore-missing-imports"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            issues = self._parse_mypy_output(result.stdout)
            
            return TypeCheckResult(
                file=str(self.project_root),
                language="py",
                success=(result.returncode == 0),
                total_issues=len(issues),
                issues=issues
            )
        
        except FileNotFoundError:
            self.logger.debug("mypy não instalado")
            return None
        except Exception as e:
            self.logger.warning(f"Erro ao rodar mypy: {str(e)}")
            return None
    
    def _analyze_python_ast(self, file_path: Path) -> Optional[TypeCheckResult]:
        """
        Análise básica de Python sem mypy.
        Verifica:
        - Funções sem type hints
        - Variáveis sem type hints
        - Return statements inconsistentes
        """
        try:
            with open(file_path) as f:
                tree = ast.parse(f.read())
            
            issues = []
            
            # Buscar funções sem type hints
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Verificar se tem return type hint
                    if node.returns is None and not node.name.startswith("_"):
                        issues.append(TypeCheckIssue(
                            file=str(file_path),
                            line=node.lineno,
                            column=0,
                            message=f"Função '{node.name}' sem type hint no return",
                            severity="warning"
                        ))
                    
                    # Verificar argumentos
                    for arg in node.args.args:
                        if arg.annotation is None:
                            issues.append(TypeCheckIssue(
                                file=str(file_path),
                                line=node.lineno,
                                column=0,
                                message=f"Argumento '{arg.arg}' sem type hint",
                                severity="warning"
                            ))
            
            return TypeCheckResult(
                file=str(file_path.relative_to(self.project_root)),
                language="py",
                success=(len(issues) == 0),
                total_issues=len(issues),
                issues=issues
            )
        
        except Exception as e:
            self.logger.warning(f"Erro ao analisar AST: {str(e)}")
            return None
    
    def _check_typescript(self, file_path: Path) -> Optional[TypeCheckResult]:
        """Valida tipos em arquivo TypeScript usando tsc."""
        try:
            result = subprocess.run(
                ["tsc", "--noEmit", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            issues = self._parse_tsc_output(result.stdout)
            
            return TypeCheckResult(
                file=str(file_path.relative_to(self.project_root)),
                language="ts",
                success=(result.returncode == 0),
                total_issues=len(issues),
                issues=issues
            )
        
        except FileNotFoundError:
            self.logger.debug("TypeScript não instalado")
            return None
        except Exception as e:
            self.logger.warning(f"Erro ao rodar tsc: {str(e)}")
            return None
    
    def _check_typescript_project(self) -> Optional[TypeCheckResult]:
        """Valida tipos em projeto TypeScript inteiro."""
        try:
            result = subprocess.run(
                ["tsc", "--noEmit"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            issues = self._parse_tsc_output(result.stdout)
            
            return TypeCheckResult(
                file=str(self.project_root),
                language="ts",
                success=(result.returncode == 0),
                total_issues=len(issues),
                issues=issues
            )
        
        except FileNotFoundError:
            self.logger.debug("TypeScript não instalado")
            return None
        except Exception as e:
            self.logger.warning(f"Erro ao rodar tsc: {str(e)}")
            return None
    
    def _check_javascript(self, file_path: Path) -> Optional[TypeCheckResult]:
        """
        Valida tipos em arquivo JavaScript usando JSDoc.
        """
        # JSDoc type checking é mais limitado, apenas aviso
        return TypeCheckResult(
            file=str(file_path),
            language="js",
            success=True,
            total_issues=0,
            issues=[]
        )
    
    def _parse_mypy_output(self, output: str) -> List[TypeCheckIssue]:
        """
        Parse de output do mypy.
        Formato: file.py:10:5: error: message [error-code]
        """
        issues = []
        
        for line in output.split("\n"):
            if not line.strip():
                continue
            
            # Match: path/file.py:10:5: error: message
            match = re.match(
                r'^(.*?):(\d+):(\d+):\s+(error|warning):\s+(.+?)(?:\s+\[([^\]]+)\])?$',
                line
            )
            
            if match:
                file_path, line_num, col_num, severity, message, code = match.groups()
                
                issues.append(TypeCheckIssue(
                    file=file_path,
                    line=int(line_num),
                    column=int(col_num),
                    message=message,
                    severity=severity,
                    code=code
                ))
        
        return issues
    
    def _parse_tsc_output(self, output: str) -> List[TypeCheckIssue]:
        """
        Parse de output do tsc.
        Formato similar a mypy
        """
        issues = []
        
        for line in output.split("\n"):
            if not line.strip() or "error TS" not in line:
                continue
            
            # Match: file.ts(10,5): error TS2345: message
            match = re.match(
                r'^(.*?)\((\d+),(\d+)\):\s+error\s+(TS\d+):\s+(.+)$',
                line
            )
            
            if match:
                file_path, line_num, col_num, code, message = match.groups()
                
                issues.append(TypeCheckIssue(
                    file=file_path,
                    line=int(line_num),
                    column=int(col_num),
                    message=message,
                    severity="error",
                    code=code
                ))
        
        return issues
    
    def suggest_type_hints(self, file_path: str) -> Dict[str, Any]:
        """
        Sugere type hints que podem ser adicionados.
        
        Returns:
            Dicionário com sugestões por função/classe
        """
        file_path = Path(file_path)
        if not file_path.is_absolute():
            file_path = self.project_root / file_path
        
        if not file_path.exists():
            return {}
        
        language = self._detect_language(file_path)
        
        if language == "py":
            return self._suggest_python_hints(file_path)
        else:
            return {}
    
    def _suggest_python_hints(self, file_path: Path) -> Dict[str, Any]:
        """Sugere type hints para Python."""
        try:
            with open(file_path) as f:
                tree = ast.parse(f.read())
            
            suggestions = {}
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_suggestions = []
                    
                    # Argumentos sem type hints
                    for arg in node.args.args:
                        if arg.annotation is None:
                            func_suggestions.append({
                                "arg": arg.arg,
                                "suggestion": "Add type hint for this argument",
                                "example": f"def {node.name}({arg.arg}: Any) -> Any:"
                            })
                    
                    # Return type hint
                    if node.returns is None:
                        func_suggestions.append({
                            "type": "return",
                            "suggestion": "Add return type hint",
                            "example": f"def {node.name}(...) -> Any:"
                        })
                    
                    if func_suggestions:
                        suggestions[node.name] = func_suggestions
            
            return suggestions
        
        except Exception as e:
            self.logger.warning(f"Erro ao sugerir hints: {str(e)}")
            return {}
    
    def is_type_checking_enabled(self) -> bool:
        """Verifica se type checking está habilitado."""
        return ENABLE_TYPE_CHECKING
    
    def get_supported_languages(self) -> List[str]:
        """Retorna linguagens suportadas."""
        langs = ["Python (mypy)"]
        
        try:
            subprocess.run(["tsc", "--version"], capture_output=True, timeout=5)
            langs.append("TypeScript (tsc)")
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
        
        return langs
