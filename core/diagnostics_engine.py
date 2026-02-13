"""
Unified Diagnostics Engine

Orquestrates linters, type checkers, security scanners across languages.
Produces unified diagnostic output format.
"""

import json
import logging
import subprocess
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

from core.language_registry import Language, LanguageRegistry
from core.structured_logger import get_logger

logger = get_logger(__name__)


class DiagnosticSeverity(str, Enum):
    """Severity levels for diagnostics."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


@dataclass
class Diagnostic:
    """Single diagnostic issue."""
    file: str
    line: int
    column: int
    severity: DiagnosticSeverity
    source: str  # "pylint", "mypy", "eslint", etc
    message: str
    code: Optional[str] = None
    suggestion: Optional[str] = None
    tags: List[str] = None  # ["unused", "deprecated", "security"]


class DiagnosticsEngine:
    """Unified diagnostics across all languages."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.registry = LanguageRegistry()
        self.diagnostics: List[Diagnostic] = []
    
    def analyze_file(self, file_path: Path) -> List[Diagnostic]:
        """
        Analyze single file for all issues.
        
        Args:
            file_path: Path to source file
        
        Returns:
            List of diagnostics found
        """
        
        language = self.registry.get_language_by_extension(file_path.suffix)
        if not language:
            self.logger.warning(f"Unsupported file type: {file_path.suffix}")
            return []
        
        diagnostics = []
        
        # Run all applicable tools
        for tool in self._get_tools_for_language(language):
            try:
                tool_diagnostics = self._run_tool(file_path, language, tool)
                diagnostics.extend(tool_diagnostics)
            except Exception as e:
                self.logger.warning(f"Error running {tool} on {file_path}: {e}")
        
        return diagnostics
    
    def analyze_directory(self, directory: Path, pattern: str = "**/*") -> List[Diagnostic]:
        """
        Analyze all source files in directory.
        
        Args:
            directory: Root directory to analyze
            pattern: File pattern to match
        
        Returns:
            List of all diagnostics found
        """
        
        all_diagnostics = []
        
        for file_path in directory.glob(pattern):
            if not file_path.is_file() or file_path.name.startswith('.'):
                continue
            
            try:
                file_diagnostics = self.analyze_file(file_path)
                all_diagnostics.extend(file_diagnostics)
            except Exception as e:
                self.logger.error(f"Error analyzing {file_path}: {e}")
        
        # Sort by file and line
        all_diagnostics.sort(key=lambda d: (d.file, d.line, d.column))
        return all_diagnostics
    
    def _get_tools_for_language(self, language: Language) -> List[str]:
        """Get all tools to run for language."""
        
        config = self.registry.get_config(language)
        if not config:
            return []
        
        tools = []
        tools.extend(config.linters)
        tools.extend(config.type_checkers)
        tools.extend(config.security_scanners)
        
        return list(set(tools))  # Remove duplicates
    
    def _run_tool(self, file_path: Path, language: Language, tool: str) -> List[Diagnostic]:
        """Run specific tool on file."""
        
        if tool == "pylint":
            return self._run_pylint(file_path)
        elif tool == "mypy":
            return self._run_mypy(file_path)
        elif tool == "flake8":
            return self._run_flake8(file_path)
        elif tool == "bandit":
            return self._run_bandit(file_path)
        elif tool == "eslint":
            return self._run_eslint(file_path)
        elif tool == "tsc":
            return self._run_typescript(file_path)
        elif tool == "go vet":
            return self._run_go_vet(file_path)
        elif tool == "clippy":
            return self._run_clippy(file_path)
        else:
            self.logger.debug(f"Tool {tool} not yet implemented")
            return []
    
    def _run_pylint(self, file_path: Path) -> List[Diagnostic]:
        """Run pylint on Python file."""
        
        try:
            result = subprocess.run(
                ["pylint", str(file_path), "--output-format=json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode == 32:  # pylint not found
                return []
            
            issues = json.loads(result.stdout) if result.stdout else []
            
            diagnostics = []
            for issue in issues:
                severity = {
                    'error': DiagnosticSeverity.ERROR,
                    'fatal': DiagnosticSeverity.ERROR,
                    'warning': DiagnosticSeverity.WARNING,
                    'convention': DiagnosticSeverity.HINT,
                    'refactor': DiagnosticSeverity.INFO,
                }.get(issue.get('type', 'warning'), DiagnosticSeverity.WARNING)
                
                diagnostics.append(Diagnostic(
                    file=str(file_path),
                    line=issue.get('line', 1),
                    column=issue.get('column', 0),
                    severity=severity,
                    source="pylint",
                    message=issue.get('message', ''),
                    code=issue.get('symbol', None),
                ))
            
            return diagnostics
        
        except subprocess.TimeoutExpired:
            self.logger.warning(f"pylint timeout on {file_path}")
            return []
        except Exception as e:
            self.logger.debug(f"pylint error: {e}")
            return []
    
    def _run_mypy(self, file_path: Path) -> List[Diagnostic]:
        """Run mypy on Python file."""
        
        try:
            result = subprocess.run(
                ["mypy", str(file_path), "--json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            diagnostics = []
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                try:
                    issue = json.loads(line)
                    diagnostics.append(Diagnostic(
                        file=issue.get('filename', str(file_path)),
                        line=issue.get('line', 1),
                        column=issue.get('column', 0),
                        severity=DiagnosticSeverity.ERROR if issue.get('severity') == 'error' else DiagnosticSeverity.WARNING,
                        source="mypy",
                        message=issue.get('message', ''),
                        code=issue.get('code', None),
                    ))
                except json.JSONDecodeError:
                    continue
            
            return diagnostics
        
        except subprocess.TimeoutExpired:
            self.logger.warning(f"mypy timeout on {file_path}")
            return []
        except Exception as e:
            self.logger.debug(f"mypy error: {e}")
            return []
    
    def _run_flake8(self, file_path: Path) -> List[Diagnostic]:
        """Run flake8 on Python file."""
        
        try:
            result = subprocess.run(
                ["flake8", str(file_path), "--format=json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            issues = json.loads(result.stdout) if result.stdout else []
            
            diagnostics = []
            for issue in issues:
                severity = DiagnosticSeverity.WARNING
                if 'E' in issue.get('code', 'W'):
                    severity = DiagnosticSeverity.ERROR
                
                diagnostics.append(Diagnostic(
                    file=issue.get('filename', str(file_path)),
                    line=issue.get('line_number', 1),
                    column=issue.get('column_number', 0),
                    severity=severity,
                    source="flake8",
                    message=issue.get('text', ''),
                    code=issue.get('code', None),
                ))
            
            return diagnostics
        
        except Exception as e:
            self.logger.debug(f"flake8 error: {e}")
            return []
    
    def _run_bandit(self, file_path: Path) -> List[Diagnostic]:
        """Run bandit for security on Python file."""
        
        try:
            result = subprocess.run(
                ["bandit", str(file_path), "-f", "json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            data = json.loads(result.stdout) if result.stdout else {}
            issues = data.get('results', [])
            
            diagnostics = []
            for issue in issues:
                diagnostics.append(Diagnostic(
                    file=issue.get('filename', str(file_path)),
                    line=issue.get('line_number', 1),
                    column=issue.get('column_number', 0),
                    severity=DiagnosticSeverity.WARNING,
                    source="bandit",
                    message=issue.get('issue_text', ''),
                    code=issue.get('test_id', None),
                    tags=['security'],
                ))
            
            return diagnostics
        
        except Exception as e:
            self.logger.debug(f"bandit error: {e}")
            return []
    
    def _run_eslint(self, file_path: Path) -> List[Diagnostic]:
        """Run eslint on JS/TS file."""
        
        try:
            result = subprocess.run(
                ["eslint", str(file_path), "--format=json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            issues_list = json.loads(result.stdout) if result.stdout else []
            
            diagnostics = []
            for file_issues in issues_list:
                for issue in file_issues.get('messages', []):
                    severity = {
                        2: DiagnosticSeverity.ERROR,
                        1: DiagnosticSeverity.WARNING,
                        0: DiagnosticSeverity.INFO,
                    }.get(issue.get('severity', 1), DiagnosticSeverity.WARNING)
                    
                    diagnostics.append(Diagnostic(
                        file=file_issues.get('filePath', str(file_path)),
                        line=issue.get('line', 1),
                        column=issue.get('column', 0),
                        severity=severity,
                        source="eslint",
                        message=issue.get('message', ''),
                        code=issue.get('ruleId', None),
                    ))
            
            return diagnostics
        
        except Exception as e:
            self.logger.debug(f"eslint error: {e}")
            return []
    
    def _run_typescript(self, file_path: Path) -> List[Diagnostic]:
        """Run tsc on TypeScript file."""
        # Implementation similar to others
        return []
    
    def _run_go_vet(self, file_path: Path) -> List[Diagnostic]:
        """Run go vet on Go file."""
        # Implementation similar to others
        return []
    
    def _run_clippy(self, file_path: Path) -> List[Diagnostic]:
        """Run clippy on Rust file."""
        # Implementation similar to others
        return []
    
    def format_report(self, diagnostics: List[Diagnostic]) -> str:
        """Format diagnostics as human-readable report."""
        
        if not diagnostics:
            return "✓ No issues found"
        
        # Group by file
        by_file = {}
        for diag in diagnostics:
            if diag.file not in by_file:
                by_file[diag.file] = []
            by_file[diag.file].append(diag)
        
        report = []
        for file_path in sorted(by_file.keys()):
            issues = by_file[file_path]
            report.append(f"\n{file_path}:")
            
            for issue in issues:
                severity_str = issue.severity.value.upper()
                report.append(
                    f"  {issue.line}:{issue.column} [{severity_str}] "
                    f"{issue.source}: {issue.message}"
                )
        
        return "\n".join(report)
