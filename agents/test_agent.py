"""
============================================================
TEST AGENT - Automated Test Execution & Coverage
============================================================
Responsável por:
- Detecção de frameworks de teste (pytest, unittest, jest)
- Execução de testes
- Coleta de cobertura de código
- Análise de resultados
- Geração de relatórios

Fluxo: Executor → Test Agent → Reviewer (bloqueia se falhar)
============================================================
"""

import subprocess
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from core.config import logger, PROJECT_ROOT, ENABLE_TEST_EXECUTION
from core.models import TestExecutionResult, TestSuiteResult, TestResult


class TestAgent:
    """Agent responsável por execução de testes."""
    
    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.project_root = project_root
        self.logger = logger
    
    def run_tests(self, test_filter: Optional[str] = None) -> Optional[TestExecutionResult]:
        """
        Executa todos os testes do projeto.
        
        Args:
            test_filter: Filtro para execução (ex: "tests/test_main.py")
        
        Returns:
            TestExecutionResult com status completo
        """
        if not ENABLE_TEST_EXECUTION:
            self.logger.info("Test execution desativado em config")
            return None
        
        # Detectar framework
        framework = self._detect_test_framework()
        
        if framework == "pytest":
            return self._run_pytest(test_filter)
        elif framework == "unittest":
            return self._run_unittest(test_filter)
        elif framework == "jest":
            return self._run_jest(test_filter)
        elif framework == "vitest":
            return self._run_vitest(test_filter)
        else:
            self.logger.info("Nenhum framework de testes detectado")
            return None
    
    def _detect_test_framework(self) -> Optional[str]:
        """Detecta qual framework de testes está sendo usado."""
        
        # Verificar pytest
        if (self.project_root / "pytest.ini").exists() or \
           (self.project_root / "setup.cfg").exists():
            return "pytest"
        
        if any(self.project_root.glob("tests/test_*.py")) or \
           any(self.project_root.glob("**/test_*.py")):
            # Verificar se pytest ou unittest
            try:
                subprocess.run(["pytest", "--version"], capture_output=True, timeout=5)
                return "pytest"
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                pass
            return "unittest"
        
        # Verificar Jest
        if (self.project_root / "jest.config.js").exists() or \
           (self.project_root / "package.json").exists():
            return "jest"
        
        # Verificar Vitest
        if (self.project_root / "vitest.config.js").exists():
            return "vitest"
        
        return None
    
    def _run_pytest(self, test_filter: Optional[str] = None) -> Optional[TestExecutionResult]:
        """Executa testes usando pytest."""
        try:
            self.logger.info("Executando pytest...")
            
            cmd = ["pytest", str(self.project_root)]
            
            if test_filter:
                cmd.append(test_filter)
            
            # Adicionar coverage se disponível
            use_coverage = True
            try:
                subprocess.run(["coverage", "--version"], capture_output=True, timeout=5)
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                use_coverage = False
            
            if use_coverage:
                cmd.extend(["--cov=.", "--cov-report=json"])
            
            cmd.extend(["-v", "--tb=short", "--json-report", "--json-report-file=/tmp/report.json"])
            
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=180
            )
            
            # Parse output
            return self._parse_pytest_output(result.stdout, result.stderr, result.returncode)
        
        except FileNotFoundError:
            self.logger.warning("pytest não instalado")
            return None
        except Exception as e:
            self.logger.error(f"Erro ao rodar pytest: {str(e)}")
            return None
    
    def _run_unittest(self, test_filter: Optional[str] = None) -> Optional[TestExecutionResult]:
        """Executa testes usando unittest."""
        try:
            self.logger.info("Executando unittest...")
            
            cmd = ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"]
            
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=180
            )
            
            # Parse output
            return self._parse_unittest_output(result.stdout, result.returncode)
        
        except Exception as e:
            self.logger.error(f"Erro ao rodar unittest: {str(e)}")
            return None
    
    def _run_jest(self, test_filter: Optional[str] = None) -> Optional[TestExecutionResult]:
        """Executa testes usando jest."""
        try:
            self.logger.info("Executando jest...")
            
            cmd = ["jest", "--coverage"]
            
            if test_filter:
                cmd.append(test_filter)
            
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=180
            )
            
            # Parse output
            return self._parse_jest_output(result.stdout, result.returncode)
        
        except FileNotFoundError:
            self.logger.warning("jest não instalado")
            return None
        except Exception as e:
            self.logger.error(f"Erro ao rodar jest: {str(e)}")
            return None
    
    def _run_vitest(self, test_filter: Optional[str] = None) -> Optional[TestExecutionResult]:
        """Executa testes usando vitest."""
        try:
            self.logger.info("Executando vitest...")
            
            cmd = ["vitest", "run", "--coverage"]
            
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=180
            )
            
            return self._parse_vitest_output(result.stdout, result.returncode)
        
        except FileNotFoundError:
            self.logger.warning("vitest não instalado")
            return None
        except Exception as e:
            self.logger.error(f"Erro ao rodar vitest: {str(e)}")
            return None
    
    def _parse_pytest_output(self, stdout: str, stderr: str, returncode: int) -> Optional[TestExecutionResult]:
        """Parse de output do pytest."""
        try:
            total_passed = 0
            total_failed = 0
            total_skipped = 0
            coverage = None
            
            # Parse summary line: "X passed, Y failed, Z skipped in Ts"
            summary_pattern = r"(\d+) passed"
            match = re.search(summary_pattern, stdout)
            if match:
                total_passed = int(match.group(1))
            
            match = re.search(r"(\d+) failed", stdout)
            if match:
                total_failed = int(match.group(1))
            
            match = re.search(r"(\d+) skipped", stdout)
            if match:
                total_skipped = int(match.group(1))
            
            # Tentar obter coverage
            match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", stdout)
            if match:
                coverage = float(match.group(1))
            
            return TestExecutionResult(
                success=(returncode == 0),
                total_suites=1,
                total_tests=total_passed + total_failed + total_skipped,
                total_passed=total_passed,
                total_failed=total_failed,
                overall_coverage=coverage,
                suites=[TestSuiteResult(
                    suite_name="pytest",
                    total_tests=total_passed + total_failed + total_skipped,
                    passed=total_passed,
                    failed=total_failed,
                    skipped=total_skipped,
                    coverage=coverage
                )]
            )
        
        except Exception as e:
            self.logger.warning(f"Erro ao parsear pytest output: {str(e)}")
            return None
    
    def _parse_unittest_output(self, output: str, returncode: int) -> Optional[TestExecutionResult]:
        """Parse de output do unittest."""
        try:
            # Parse format: "Ran X tests in Ys"
            match = re.search(r"Ran (\d+) test", output)
            total_tests = int(match.group(1)) if match else 0
            
            # Contar failures/errors
            failed = output.count("FAIL:")
            errors = output.count("ERROR:")
            total_failed = failed + errors
            total_passed = total_tests - total_failed
            
            return TestExecutionResult(
                success=(returncode == 0),
                total_suites=1,
                total_tests=total_tests,
                total_passed=total_passed,
                total_failed=total_failed,
                suites=[TestSuiteResult(
                    suite_name="unittest",
                    total_tests=total_tests,
                    passed=total_passed,
                    failed=total_failed
                )]
            )
        
        except Exception as e:
            self.logger.warning(f"Erro ao parsear unittest output: {str(e)}")
            return None
    
    def _parse_jest_output(self, output: str, returncode: int) -> Optional[TestExecutionResult]:
        """Parse de output do jest."""
        try:
            # Parse format: "Tests: X passed, Y failed, Z total"
            match = re.search(r"Tests:\s+(\d+) passed", output)
            total_passed = int(match.group(1)) if match else 0
            
            match = re.search(r"(\d+) failed", output)
            total_failed = int(match.group(1)) if match else 0
            
            # Coverage
            match = re.search(r"Coverage summary.*?Statements\s+:\s+(\d+(?:\.\d+)?)", output, re.DOTALL)
            coverage = float(match.group(1)) if match else None
            
            return TestExecutionResult(
                success=(returncode == 0),
                total_suites=1,
                total_tests=total_passed + total_failed,
                total_passed=total_passed,
                total_failed=total_failed,
                overall_coverage=coverage,
                suites=[TestSuiteResult(
                    suite_name="jest",
                    total_tests=total_passed + total_failed,
                    passed=total_passed,
                    failed=total_failed,
                    coverage=coverage
                )]
            )
        
        except Exception as e:
            self.logger.warning(f"Erro ao parsear jest output: {str(e)}")
            return None
    
    def _parse_vitest_output(self, output: str, returncode: int) -> Optional[TestExecutionResult]:
        """Parse de output do vitest."""
        # Similar a jest
        return self._parse_jest_output(output, returncode)
    
    def get_coverage_report(self) -> Optional[Dict[str, Any]]:
        """
        Obtém relatório de cobertura.
        """
        try:
            # Procurar por arquivo de cobertura .coverage
            coverage_file = self.project_root / ".coverage"
            json_file = self.project_root / "coverage.json"
            
            if json_file.exists():
                with open(json_file) as f:
                    return json.load(f)
            
            # Tentar gerar via coverage.py
            result = subprocess.run(
                ["coverage", "json"],
                cwd=str(self.project_root),
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0 and json_file.exists():
                with open(json_file) as f:
                    return json.load(f)
        
        except Exception as e:
            self.logger.debug(f"Erro ao obter coverage report: {str(e)}")
        
        return None
    
    def is_test_execution_enabled(self) -> bool:
        """Verifica se execução de testes está habilitada."""
        return ENABLE_TEST_EXECUTION
    
    def generate_test_report(self, result: TestExecutionResult) -> str:
        """Gera relatório de testes em formato legível."""
        report = "\n" + "=" * 60 + "\n"
        report += "TEST EXECUTION REPORT\n"
        report += "=" * 60 + "\n\n"
        
        report += f"Overall Status: {'✓ PASSED' if result.success else '✗ FAILED'}\n"
        report += f"Total Tests: {result.total_tests}\n"
        report += f"Passed: {result.total_passed}\n"
        report += f"Failed: {result.total_failed}\n"
        
        if result.overall_coverage:
            report += f"Coverage: {result.overall_coverage:.1f}%\n"
        
        report += "\n" + "=" * 60 + "\n"
        
        return report
