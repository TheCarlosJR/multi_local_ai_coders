"""
============================================================
STATIC ANALYSIS AGENT - Code Quality & Security Scanning
============================================================
Responsável por:
- Análise estática (pylint, flake8, black)
- Code smell detection
- Segurança (bandit)
- Complexidade ciclomática
- Estilo de código

Fluxo: CI/CD → Static Analysis (pré-check) → Executor
       Executor → Static Analysis (pós-check) → Reviewer
============================================================
"""

import subprocess
import re
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from core.config import logger, PROJECT_ROOT, ENABLE_STATIC_ANALYSIS
from core.models import AnalysisResult, AnalysisIssue


class StaticAnalysisAgent:
    """Agent responsável por análise estática de código."""
    
    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.project_root = project_root
        self.logger = logger
    
    def analyze_file(self, file_path: str) -> Optional[AnalysisResult]:
        """
        Analisa um arquivo específico.
        
        Args:
            file_path: Caminho do arquivo
        
        Returns:
            AnalysisResult com violations encontradas
        """
        file_path = Path(file_path)
        if not file_path.is_absolute():
            file_path = self.project_root / file_path
        
        if not file_path.exists():
            return None
        
        # Detectar linguagem
        suffix = file_path.suffix.lower()
        
        if suffix == ".py":
            return self._analyze_python(file_path)
        elif suffix == ".ts" or suffix == ".tsx":
            return self._analyze_typescript(file_path)
        elif suffix == ".js" or suffix == ".jsx":
            return self._analyze_javascript(file_path)
        else:
            return None
    
    def analyze_project(self) -> Optional[AnalysisResult]:
        """Analisa todo o projeto."""
        
        if not ENABLE_STATIC_ANALYSIS:
            return None
        
        # Detectar principais arquivos
        py_files = list(self.project_root.glob("**/*.py"))
        
        if py_files:
            return self._analyze_python_project()
        
        return None
    
    def _analyze_python(self, file_path: Path) -> Optional[AnalysisResult]:
        """Análise Python com pylint e flake8."""
        try:
            self.logger.info(f"Analisando Python: {file_path.name}...")
            
            issues = []
            
            # Rodar pylint
            try:
                issues.extend(self._run_pylint(file_path))
            except Exception as e:
                self.logger.debug(f"pylint falhou: {str(e)}")
            
            # Rodar flake8
            try:
                issues.extend(self._run_flake8(file_path))
            except Exception as e:
                self.logger.debug(f"flake8 falhou: {str(e)}")
            
            # Rodar bandit (segurança)
            try:
                security_issues = self._run_bandit(file_path)
                for issue in security_issues:
                    issue.tool = "bandit"
                issues.extend(security_issues)
            except Exception as e:
                self.logger.debug(f"bandit falhou: {str(e)}")
            
            # Remover duplicatas
            unique_issues = {(i.file, i.line, i.message): i for i in issues}
            
            return AnalysisResult(
                file=str(file_path.relative_to(self.project_root)),
                language="py",
                total_violations=len(unique_issues),
                violations=list(unique_issues.values())
            )
        
        except Exception as e:
            self.logger.warning(f"Erro ao analisar Python: {str(e)}")
            return None
    
    def _analyze_python_project(self) -> Optional[AnalysisResult]:
        """Análise Python de todo o projeto."""
        try:
            self.logger.info("Analisando projeto Python...")
            
            issues = []
            
            # Rodar pylint no projeto inteiro
            try:
                result = subprocess.run(
                    ["pylint", str(self.project_root), "--output-format=json", "--exit-zero"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.stdout:
                    data = json.loads(result.stdout)
                    for item in data:
                        issues.append(AnalysisIssue(
                            file=item.get("path", ""),
                            line=item.get("line", 0),
                            column=item.get("column", 0),
                            message=item.get("message", ""),
                            code=item.get("symbol", ""),
                            severity="error" if item.get("type") == "error" else "warning",
                            tool="pylint"
                        ))
            except FileNotFoundError:
                self.logger.debug("pylint não disponível")
            except json.JSONDecodeError:
                self.logger.debug("Erro ao parsear output pylint")
            except Exception as e:
                self.logger.debug(f"Erro com pylint: {str(e)}")
            
            return AnalysisResult(
                file=str(self.project_root),
                language="py",
                total_violations=len(issues),
                violations=issues
            )
        
        except Exception as e:
            self.logger.warning(f"Erro ao analisar projeto: {str(e)}")
            return None
    
    def _analyze_typescript(self, file_path: Path) -> Optional[AnalysisResult]:
        """Análise TypeScript com eslint."""
        try:
            self.logger.info(f"Analisando TypeScript: {file_path.name}...")
            
            issues = self._run_eslint(file_path)
            
            return AnalysisResult(
                file=str(file_path.relative_to(self.project_root)),
                language="ts",
                total_violations=len(issues),
                violations=issues
            )
        
        except Exception as e:
            self.logger.warning(f"Erro ao analisar TypeScript: {str(e)}")
            return None
    
    def _analyze_javascript(self, file_path: Path) -> Optional[AnalysisResult]:
        """Análise JavaScript com eslint."""
        return self._analyze_typescript(file_path)  # Mesmo process
    
    def _run_pylint(self, file_path: Path) -> List[AnalysisIssue]:
        """Executa pylint em um arquivo."""
        try:
            result = subprocess.run(
                ["pylint", str(file_path), "--output-format=json", "--exit-zero"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if not result.stdout:
                return []
            
            data = json.loads(result.stdout)
            issues = []
            
            for item in data:
                issues.append(AnalysisIssue(
                    file=str(file_path),
                    line=item.get("line", 0),
                    column=item.get("column", 0),
                    message=item.get("message", ""),
                    code=item.get("symbol", ""),
                    severity="error" if item.get("type") == "error" else "warning",
                    tool="pylint"
                ))
            
            return issues
        
        except FileNotFoundError:
            return []
        except Exception as e:
            self.logger.debug(f"Erro ao rodar pylint: {str(e)}")
            return []
    
    def _run_flake8(self, file_path: Path) -> List[AnalysisIssue]:
        """Executa flake8 em um arquivo."""
        try:
            result = subprocess.run(
                ["flake8", str(file_path), "--format=json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if not result.stdout:
                return []
            
            data = json.loads(result.stdout)
            issues = []
            
            for item in data:
                issues.append(AnalysisIssue(
                    file=str(file_path),
                    line=item.get("line_number", 0),
                    column=item.get("column_number", 0),
                    message=item.get("text", ""),
                    code=item.get("code", ""),
                    severity="warning",
                    tool="flake8"
                ))
            
            return issues
        
        except FileNotFoundError:
            return []
        except Exception as e:
            self.logger.debug(f"Erro ao rodar flake8: {str(e)}")
            return []
    
    def _run_bandit(self, file_path: Path) -> List[AnalysisIssue]:
        """Executa bandit (segurança) em um arquivo."""
        try:
            result = subprocess.run(
                ["bandit", str(file_path), "-f", "json", "-ll"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if not result.stdout:
                return []
            
            data = json.loads(result.stdout)
            issues = []
            
            for result_item in data.get("results", []):
                issues.append(AnalysisIssue(
                    file=str(file_path),
                    line=result_item.get("line_number", 0),
                    column=0,
                    message=result_item.get("issue_text", ""),
                    code=result_item.get("test_id", ""),
                    severity="error",
                    tool="bandit"
                ))
            
            return issues
        
        except FileNotFoundError:
            return []
        except Exception as e:
            self.logger.debug(f"Erro ao rodar bandit: {str(e)}")
            return []
    
    def _run_eslint(self, file_path: Path) -> List[AnalysisIssue]:
        """Executa eslint em um arquivo."""
        try:
            result = subprocess.run(
                ["eslint", str(file_path), "--format=json"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.project_root)
            )
            
            if not result.stdout:
                return []
            
            data = json.loads(result.stdout)
            issues = []
            
            for file_report in data:
                for message in file_report.get("messages", []):
                    issues.append(AnalysisIssue(
                        file=file_report.get("filePath", str(file_path)),
                        line=message.get("line", 0),
                        column=message.get("column", 0),
                        message=message.get("message", ""),
                        code=message.get("ruleId", ""),
                        severity="error" if message.get("severity") == 2 else "warning",
                        tool="eslint"
                    ))
            
            return issues
        
        except FileNotFoundError:
            return []
        except Exception as e:
            self.logger.debug(f"Erro ao rodar eslint: {str(e)}")
            return []
    
    def estimate_complexity(self, file_path: str) -> Optional[float]:
        """
        Estima complexidade ciclomática de um arquivo.
        
        Returns:
            Score de complexidade (0-100)
        """
        file_path = Path(file_path)
        if not file_path.is_absolute():
            file_path = self.project_root / file_path
        
        if not file_path.exists():
            return None
        
        try:
            # Usar radon para complexidade
            result = subprocess.run(
                ["radon", "cc", str(file_path), "-s", "-j"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                # Extrair complexidade média
                values = list(data.values())
                if values:
                    return sum(v.get("complexity", 0) for v in values) / len(values)
        
        except FileNotFoundError:
            self.logger.debug("radon não instalado")
        except Exception as e:
            self.logger.debug(f"Erro ao calcular complexidade: {str(e)}")
        
        return None
    
    def get_supported_tools(self) -> List[str]:
        """Retorna lista de ferramentas de análise disponíveis."""
        tools = []
        
        for tool in ["pylint", "flake8", "bandit", "eslint", "radon"]:
            try:
                subprocess.run(
                    [tool, "--version"],
                    capture_output=True,
                    timeout=5
                )
                tools.append(tool)
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                pass
        
        return tools
    
    def is_analysis_enabled(self) -> bool:
        """Verifica se análise estática está habilitada."""
        return ENABLE_STATIC_ANALYSIS
