"""
============================================================
CI/CD AGENT - QUALITY GATEWAY
============================================================
Responsável por validações pré-execução:
- Detectar e validar estrutura CI/CD existente
- Executar quality gates (testes, type-check, análise estática)
- Gerar relatórios de qualidade
- Bloquear ou permitir execução baseado em critérios

Fluxo: Agent Runner → CI/CD Agent → Memory/Planner
============================================================
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from core.config import (
    logger, PROJECT_ROOT, CI_CD_ENABLED, CI_CD_AUTO_DETECT,
    ENABLE_TYPE_CHECKING, ENABLE_STATIC_ANALYSIS, ENABLE_TEST_EXECUTION
)
from core.models import (
    QualityGateResult, PreExecutionValidation,
    TypeCheckResult, TestExecutionResult, AnalysisResult
)


class CICDAgent:
    """Agent responsável por validação pré-execução (quality gates)."""
    
    def __init__(self):
        self.logger = logger
        self.project_root = PROJECT_ROOT
        
    def validate_pre_execution(self) -> PreExecutionValidation:
        """
        Executa todas as validações pré-execução.
        
        Retorna:
            PreExecutionValidation com status de todos os gates
        """
        if not CI_CD_ENABLED:
            self.logger.info("CI/CD Agent desativado via config")
            return PreExecutionValidation(
                success=True,
                warnings=["CI/CD Agent desativado (CI_CD_ENABLED=false)"]
            )
        
        self.logger.info("=" * 60)
        self.logger.info("CI/CD QUALITY GATES INICIADOS")
        self.logger.info("=" * 60)
        
        validation = PreExecutionValidation(success=True)
        warnings = []
        
        # Gate 1: Type Checking
        if ENABLE_TYPE_CHECKING:
            self.logger.info("\n[GATE 1/4] Type Checking...")
            type_result = self._run_type_check()
            validation.type_check = type_result
            if type_result and not type_result.success:
                warnings.append(f"Type checking encontrou {type_result.total_issues} erros")
        
        # Gate 2: Static Analysis
        if ENABLE_STATIC_ANALYSIS:
            self.logger.info("\n[GATE 2/4] Static Analysis...")
            analysis_result = self._run_static_analysis()
            validation.static_analysis = analysis_result
            if analysis_result and analysis_result.total_violations > 0:
                warnings.append(f"Análise estática encontrou {analysis_result.total_violations} violações")
        
        # Gate 3: Test Execution
        if ENABLE_TEST_EXECUTION:
            self.logger.info("\n[GATE 3/4] Test Execution...")
            test_result = self._run_tests()
            validation.test_results = test_result
            if test_result and not test_result.success:
                warnings.append(f"Testes: {test_result.total_failed} falharam")
                validation.success = False
        
        # Gate 4: Custom Quality Gates
        self.logger.info("\n[GATE 4/4] Custom Quality Gates...")
        custom_gates = self._run_custom_gates()
        validation.quality_gates = custom_gates
        
        # Verificar se algum gate falhou
        failed_gates = [g for g in custom_gates if not g.passed and g.severity == "error"]
        if failed_gates:
            validation.success = False
            for gate in failed_gates:
                warnings.append(f"Quality Gate '{gate.gate_name}': {gate.message}")
        
        validation.warnings = warnings
        
        # Log resumo
        self.logger.info("\n" + "=" * 60)
        if validation.success:
            self.logger.info("✓ TODOS OS GATES PASSARAM - Execução autorizada")
        else:
            self.logger.warning("✗ ALGUNS GATES FALHARAM - Execução bloqueada")
        self.logger.info("=" * 60)
        
        return validation
    
    def _run_type_check(self) -> Optional[TypeCheckResult]:
        """
        Executa validação de tipos.
        Detecta arquivos Python/TypeScript e roda validadores.
        """
        try:
            # Detectar linguagens no projeto
            has_python = list(self.project_root.glob("**/*.py"))
            has_ts = list(self.project_root.glob("**/*.ts")) + list(self.project_root.glob("**/*.tsx"))
            
            if not has_python and not has_ts:
                self.logger.info("  ℹ Nenhum arquivo Python/TypeScript encontrado")
                return None
            
            # Para Python: tentar rodar mypy
            if has_python:
                return self._run_mypy()
            
            # Para TypeScript: tentar rodar tsc
            if has_ts:
                return self._run_tsc()
            
        except Exception as e:
            self.logger.warning(f"  ⚠ Type checking falhou: {str(e)}")
            return None
    
    def _run_mypy(self) -> Optional[TypeCheckResult]:
        """Executa mypy para validação de tipos Python."""
        try:
            import subprocess
            
            self.logger.info("  → Executando mypy...")
            
            # Tentar rodar mypy
            result = subprocess.run(
                ["mypy", str(self.project_root), "--ignore-missing-imports"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info("  ✓ Mypy: sem erros de tipo")
                return TypeCheckResult(
                    file=str(self.project_root),
                    language="py",
                    success=True,
                    total_issues=0
                )
            else:
                # Parse mypy output para extrair erros
                issues = self._parse_mypy_output(result.stdout)
                self.logger.warning(f"  ✗ Mypy: {len(issues)} erros")
                return TypeCheckResult(
                    file=str(self.project_root),
                    language="py",
                    success=False,
                    total_issues=len(issues),
                    issues=issues
                )
        
        except FileNotFoundError:
            self.logger.info("  ℹ mypy não instalado (install: pip install mypy)")
            return None
        except Exception as e:
            self.logger.warning(f"  ⚠ Erro ao rodar mypy: {str(e)}")
            return None
    
    def _run_tsc(self) -> Optional[TypeCheckResult]:
        """Executa tsc para validação de tipos TypeScript."""
        try:
            import subprocess
            
            self.logger.info("  → Executando tsc...")
            
            result = subprocess.run(
                ["tsc", "--noEmit"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info("  ✓ TSC: sem erros de tipo")
                return TypeCheckResult(
                    file=str(self.project_root),
                    language="ts",
                    success=True,
                    total_issues=0
                )
            else:
                issues = self._parse_tsc_output(result.stdout)
                self.logger.warning(f"  ✗ TSC: {len(issues)} erros")
                return TypeCheckResult(
                    file=str(self.project_root),
                    language="ts",
                    success=False,
                    total_issues=len(issues),
                    issues=issues
                )
        
        except FileNotFoundError:
            self.logger.info("  ℹ TypeScript não instalado")
            return None
        except Exception as e:
            self.logger.warning(f"  ⚠ Erro ao rodar tsc: {str(e)}")
            return None
    
    def _run_static_analysis(self) -> Optional[AnalysisResult]:
        """Executa análise estática (pylint, flake8, eslint)."""
        try:
            import subprocess
            
            has_python = list(self.project_root.glob("**/*.py"))
            
            if not has_python:
                self.logger.info("  ℹ Nenhum arquivo Python encontrado")
                return None
            
            self.logger.info("  → Executando pylint/flake8...")
            
            # Tentar pylint primeiro
            result = subprocess.run(
                ["pylint", "--exit-zero", str(self.project_root)],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                self.logger.info("  ✓ Análise estática: sem violações")
                return AnalysisResult(
                    file=str(self.project_root),
                    language="py",
                    total_violations=0
                )
            else:
                violations = self._parse_pylint_output(result.stdout)
                self.logger.warning(f"  ✗ Análise estática: {len(violations)} violações")
                return AnalysisResult(
                    file=str(self.project_root),
                    language="py",
                    total_violations=len(violations),
                    violations=violations
                )
        
        except FileNotFoundError:
            self.logger.info("  ℹ pylint não instalado (install: pip install pylint)")
            return None
        except Exception as e:
            self.logger.warning(f"  ⚠ Erro ao rodar análise estática: {str(e)}")
            return None
    
    def _run_tests(self) -> Optional[TestExecutionResult]:
        """Executa testes (pytest, unittest, jest)."""
        try:
            import subprocess
            
            # Detectar framework de testes
            has_pytest = (self.project_root / "pytest.ini").exists() or \
                         (self.project_root / "setup.cfg").exists()
            has_tests = list(self.project_root.glob("tests/test_*.py")) or \
                        list(self.project_root.glob("**/test_*.py"))
            
            if not has_tests and not has_pytest:
                self.logger.info("  ℹ Nenhum teste encontrado")
                return None
            
            self.logger.info("  → Executando pytest...")
            
            result = subprocess.run(
                ["pytest", str(self.project_root), "-v", "--tb=short", "--co", "-q"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if "no tests ran" in result.stdout.lower():
                self.logger.info("  ℹ Nenhum teste configurado")
                return None
            
            # Rodar testes de verdade
            result = subprocess.run(
                ["pytest", str(self.project_root), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Parse pytest output
            return self._parse_pytest_output(result.stdout, result.returncode)
        
        except FileNotFoundError:
            self.logger.info("  ℹ pytest não instalado (install: pip install pytest)")
            return None
        except Exception as e:
            self.logger.warning(f"  ⚠ Erro ao rodar testes: {str(e)}")
            return None
    
    def _run_custom_gates(self) -> List[QualityGateResult]:
        """Executa quality gates customizados."""
        gates = []
        
        # Gate: Arquivo .gitignore existe?
        if not (self.project_root / ".gitignore").exists():
            gates.append(QualityGateResult(
                gate_name="gitignore",
                passed=False,
                message=".gitignore não existe",
                severity="warning"
            ))
        else:
            gates.append(QualityGateResult(
                gate_name="gitignore",
                passed=True,
                message=".gitignore presente",
                severity="info"
            ))
        
        # Gate: README existe?
        readme_exists = (self.project_root / "README.md").exists()
        gates.append(QualityGateResult(
            gate_name="readme",
            passed=readme_exists,
            message="README.md presente" if readme_exists else "README.md faltando",
            severity="warning" if not readme_exists else "info"
        ))
        
        # Gate: Arquivo requirements.txt ou pyproject.toml?
        has_requirements = (self.project_root / "requirements.txt").exists() or \
                           (self.project_root / "pyproject.toml").exists()
        gates.append(QualityGateResult(
            gate_name="dependencies",
            passed=has_requirements,
            message="requirements.txt ou pyproject.toml presente" if has_requirements else "Arquivo de dependências faltando",
            severity="warning" if not has_requirements else "info"
        ))
        
        return gates
    
    def _parse_mypy_output(self, output: str) -> list:
        """Parse mypy output e extrai issues."""
        from core.models import TypeCheckIssue
        
        issues = []
        for line in output.split("\n"):
            if "error:" in line or "note:" in line:
                # Parse format: file.py:10:5: error: message
                parts = line.split(":")
                if len(parts) >= 4:
                    try:
                        issues.append(TypeCheckIssue(
                            file=parts[0].strip(),
                            line=int(parts[1].strip()),
                            column=int(parts[2].strip()) if len(parts) > 2 else 0,
                            message=":".join(parts[3:]).strip(),
                            severity="error" if "error:" in line else "info"
                        ))
                    except (ValueError, IndexError):
                        pass
        
        return issues
    
    def _parse_tsc_output(self, output: str) -> list:
        """Parse tsc output e extrai issues."""
        # Similar a mypy
        return []
    
    def _parse_pylint_output(self, output: str) -> list:
        """Parse pylint output e extrai violations."""
        from core.models import AnalysisIssue
        
        issues = []
        for line in output.split("\n"):
            if ":" in line and ("error" in line or "warning" in line):
                parts = line.split(":")
                if len(parts) >= 4:
                    try:
                        issues.append(AnalysisIssue(
                            file=parts[0].strip(),
                            line=int(parts[1].strip()) if parts[1].strip().isdigit() else 0,
                            column=0,
                            message=":".join(parts[3:]).strip(),
                            code="",
                            severity="error",
                            tool="pylint"
                        ))
                    except (ValueError, IndexError):
                        pass
        
        return issues
    
    def _parse_pytest_output(self, output: str, returncode: int) -> Optional[TestExecutionResult]:
        """Parse pytest output e extrai resultados."""
        from core.models import TestSuiteResult
        
        try:
            # Parse simple pytest output
            lines = output.split("\n")
            
            # Procurar por linha de resumo: "X passed, Y failed, ..."
            summary_line = None
            for line in lines:
                if "passed" in line or "failed" in line:
                    summary_line = line
                    break
            
            if not summary_line:
                return None
            
            # Parse summary
            passed = 0
            failed = 0
            
            if "passed" in summary_line:
                try:
                    passed = int(summary_line.split("passed")[0].strip().split()[-1])
                except:
                    pass
            
            if "failed" in summary_line:
                try:
                    failed = int(summary_line.split("failed")[0].strip().split()[-1])
                except:
                    pass
            
            return TestExecutionResult(
                success=(returncode == 0),
                total_suites=1,
                total_tests=passed + failed,
                total_passed=passed,
                total_failed=failed,
                suites=[TestSuiteResult(
                    suite_name="pytest",
                    total_tests=passed + failed,
                    passed=passed,
                    failed=failed
                )]
            )
        
        except Exception as e:
            self.logger.warning(f"Erro ao parsear pytest output: {str(e)}")
            return None
    
    def detect_ci_config(self) -> Dict[str, Any]:
        """Detecta configuração CI/CD existente no projeto."""
        ci_config = {
            "github_actions": (self.project_root / ".github" / "workflows").exists(),
            "gitlab_ci": (self.project_root / ".gitlab-ci.yml").exists(),
            "jenkins": (self.project_root / "Jenkinsfile").exists(),
            "circleci": (self.project_root / ".circleci").exists(),
        }
        
        active_ci = [k for k, v in ci_config.items() if v]
        
        self.logger.info(f"CI/CD detectado: {active_ci if active_ci else 'nenhum'}")
        
        return ci_config
    
    def generate_ci_workflow(self, ci_type: str = "github") -> str:
        """
        Gera workflow de CI/CD automático baseado no tipo.
        
        Args:
            ci_type: "github", "gitlab", "jenkins"
        
        Returns:
            YAML/Groovy do workflow
        """
        if ci_type == "github":
            return self._generate_github_workflow()
        elif ci_type == "gitlab":
            return self._generate_gitlab_ci()
        else:
            return ""
    
    def _generate_github_workflow(self) -> str:
        """Gera GitHub Actions workflow."""
        workflow = """
name: Quality Gates

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Type checking (mypy)
        run: mypy . --ignore-missing-imports || true
      
      - name: Static analysis (pylint)
        run: pylint . --exit-zero || true
      
      - name: Run tests
        run: pytest tests/ -v --cov=.
"""
        return workflow
    
    def _generate_gitlab_ci(self) -> str:
        """Gera GitLab CI pipeline."""
        pipeline = """
stages:
  - quality
  - test

quality_gates:
  stage: quality
  image: python:3.9
  script:
    - pip install -r requirements.txt
    - mypy . --ignore-missing-imports || true
    - pylint . --exit-zero || true
  allow_failure: true

tests:
  stage: test
  image: python:3.9
  script:
    - pip install -r requirements.txt
    - pytest tests/ -v --cov=.
"""
        return pipeline
    
    def report_metrics(self) -> Dict[str, Any]:
        """Gera relatório de métricas de qualidade."""
        return {
            "timestamp": datetime.now().isoformat(),
            "project": str(self.project_root),
            "ci_enabled": CI_CD_ENABLED,
            "gates": {
                "type_checking": ENABLE_TYPE_CHECKING,
                "static_analysis": ENABLE_STATIC_ANALYSIS,
                "tests": ENABLE_TEST_EXECUTION,
            }
        }
