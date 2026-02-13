"""
============================================================
CI/CD TOOL - Helpers e wrappers para operações CI/CD
============================================================
Fornece funções auxiliares para:
- Detectar estrutura de CI/CD
- Executar scripts de build/test
- Gerar e atualizar CI files
- Reportagem de resultados
============================================================
"""

import os
import subprocess
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from core.config import logger, PROJECT_ROOT


class CICDTool:
    """Tool auxiliar para operações CI/CD."""
    
    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.project_root = project_root
        self.logger = logger
    
    def detect_build_system(self) -> Dict[str, bool]:
        """Detecta qual sistema de build é usado."""
        systems = {
            "poetry": (self.project_root / "pyproject.toml").exists() and 
                      "tool.poetry" in (self.project_root / "pyproject.toml").read_text(),
            "pip": (self.project_root / "requirements.txt").exists(),
            "npm": (self.project_root / "package.json").exists(),
            "pip_venv": (self.project_root / ".venv").exists(),
            "conda": (self.project_root / "environment.yml").exists(),
        }
        return {k: v for k, v in systems.items() if v}
    
    def detect_test_framework(self) -> Dict[str, bool]:
        """Detecta qual framework de testes é usado."""
        frameworks = {
            "pytest": self._has_pytest(),
            "unittest": self._has_unittest(),
            "jest": self._has_jest(),
            "vitest": self._has_vitest(),
            "mocha": self._has_mocha(),
        }
        return {k: v for k, v in frameworks.items() if v}
    
    def _has_pytest(self) -> bool:
        """Verifica se pytest está disponível."""
        return (
            (self.project_root / "pytest.ini").exists() or
            (self.project_root / "setup.cfg").exists() or
            (self.project_root / "pyproject.toml").exists()
        ) and any(self.project_root.glob("tests/test_*.py")) or any(self.project_root.glob("**/test_*.py"))
    
    def _has_unittest(self) -> bool:
        """Verifica se unittest está sendo usado."""
        return any(self.project_root.glob("**/test_*.py"))
    
    def _has_jest(self) -> bool:
        """Verifica se jest está configurado."""
        return (self.project_root / "jest.config.js").exists()
    
    def _has_vitest(self) -> bool:
        """Verifica se vitest está configurado."""
        return (self.project_root / "vitest.config.js").exists()
    
    def _has_mocha(self) -> bool:
        """Verifica se mocha está configurado."""
        return (self.project_root / ".mocharc.js").exists() or \
               (self.project_root / ".mocharc.json").exists()
    
    def execute_build(self) -> Tuple[bool, str]:
        """
        Executa build conforme sistema detectado.
        
        Returns:
            (success, output)
        """
        build_system = self.detect_build_system()
        
        if "poetry" in build_system:
            return self._run_poetry_build()
        elif "npm" in build_system:
            return self._run_npm_build()
        elif "pip" in build_system:
            return self._run_pip_install()
        else:
            return (True, "Nenhum build system detectado")
    
    def _run_poetry_build(self) -> Tuple[bool, str]:
        """Executa build com Poetry."""
        try:
            result = subprocess.run(
                ["poetry", "install"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=120
            )
            return (result.returncode == 0, result.stdout + result.stderr)
        except Exception as e:
            return (False, str(e))
    
    def _run_npm_build(self) -> Tuple[bool, str]:
        """Executa build com npm."""
        try:
            result = subprocess.run(
                ["npm", "install"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=120
            )
            return (result.returncode == 0, result.stdout + result.stderr)
        except Exception as e:
            return (False, str(e))
    
    def _run_pip_install(self) -> Tuple[bool, str]:
        """Executa install com pip."""
        try:
            result = subprocess.run(
                ["pip", "install", "-r", "requirements.txt"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=120
            )
            return (result.returncode == 0, result.stdout + result.stderr)
        except Exception as e:
            return (False, str(e))
    
    def get_github_workflows(self) -> List[Path]:
        """Lista todos workflows do GitHub Actions."""
        workflows_dir = self.project_root / ".github" / "workflows"
        if workflows_dir.exists():
            return list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
        return []
    
    def read_github_workflow(self, workflow_name: str) -> Optional[Dict]:
        """Lê um workflow do GitHub Actions."""
        workflow_file = self.project_root / ".github" / "workflows" / f"{workflow_name}.yml"
        
        if workflow_file.exists():
            try:
                with open(workflow_file) as f:
                    return yaml.safe_load(f)
            except Exception as e:
                self.logger.error(f"Erro ao ler workflow: {str(e)}")
                return None
        
        return None
    
    def create_github_workflow(self, name: str, content: str) -> bool:
        """Cria um novo workflow do GitHub Actions."""
        workflows_dir = self.project_root / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        
        workflow_file = workflows_dir / f"{name}.yml"
        
        try:
            with open(workflow_file, "w") as f:
                f.write(content)
            self.logger.info(f"Workflow criado: {workflow_file}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao criar workflow: {str(e)}")
            return False
    
    def get_gitlab_ci_config(self) -> Optional[Dict]:
        """Lê configuração GitLab CI."""
        gitlab_file = self.project_root / ".gitlab-ci.yml"
        
        if gitlab_file.exists():
            try:
                with open(gitlab_file) as f:
                    return yaml.safe_load(f)
            except Exception as e:
                self.logger.error(f"Erro ao ler .gitlab-ci.yml: {str(e)}")
                return None
        
        return None
    
    def create_gitlab_ci_config(self, content: str) -> bool:
        """Cria arquivo .gitlab-ci.yml."""
        gitlab_file = self.project_root / ".gitlab-ci.yml"
        
        try:
            with open(gitlab_file, "w") as f:
                f.write(content)
            self.logger.info(f"GitLab CI config criado: {gitlab_file}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao criar .gitlab-ci.yml: {str(e)}")
            return False
    
    def save_quality_report(self, report: Dict) -> bool:
        """Salva relatório de qualidade em arquivo."""
        try:
            # Criar diretório de relatórios
            reports_dir = self.project_root / "reports"
            reports_dir.mkdir(exist_ok=True)
            
            # Salvar como JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = reports_dir / f"quality_report_{timestamp}.json"
            
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(f"Relatório salvo: {report_file}")
            return True
        
        except Exception as e:
            self.logger.error(f"Erro ao salvar relatório: {str(e)}")
            return False
    
    def merge_ci_configs(self, existing: Dict, new: Dict) -> Dict:
        """Mescla configuração CI existente com nova."""
        # Lógica simples de merge - pode ser expandida
        merged = existing.copy()
        
        # Adicionar jobs novos
        if "jobs" in new:
            if "jobs" not in merged:
                merged["jobs"] = {}
            merged["jobs"].update(new["jobs"])
        
        return merged
    
    def export_ci_report(self, output_format: str = "json") -> str:
        """Exporta relatório de CI em diferentes formatos."""
        ci_info = {
            "timestamp": datetime.now().isoformat(),
            "project": str(self.project_root),
            "build_system": self.detect_build_system(),
            "test_framework": self.detect_test_framework(),
            "ci_platforms": {
                "github_actions": len(self.get_github_workflows()) > 0,
                "gitlab_ci": self.get_gitlab_ci_config() is not None,
            }
        }
        
        if output_format == "json":
            return json.dumps(ci_info, indent=2)
        elif output_format == "yaml":
            return yaml.dump(ci_info)
        else:
            return str(ci_info)
