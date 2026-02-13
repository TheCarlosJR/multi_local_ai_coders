"""
Project Structure Analyzer

Analyzes project to understand:
- Build system (Maven, Gradle, Poetry, npm, etc)
- Dependencies and their security status
- File organization and patterns
- Entry points and main modules
- Architectural patterns used

Outputs: project_metadata.json
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import re

from core.structured_logger import get_logger
from core.language_registry import LanguageRegistry

logger = get_logger(__name__)


@dataclass
class DependencyInfo:
    """Info about a dependency."""
    name: str
    version: Optional[str] = None
    security_status: str = "unknown"  # ok, vulnerable, deprecated
    scope: str = "runtime"  # runtime, dev, optional


@dataclass
class FileInfo:
    """Info about a source file."""
    path: str
    language: str
    imports: List[str]
    exports: List[str]
    complexity: int  # Cyclomatic complexity estimate
    is_test: bool = False


@dataclass
class ProjectMetadata:
    """Complete project metadata."""
    build_system: Optional[str]
    languages: List[str]
    entry_points: List[str]
    dependencies: Dict[str, DependencyInfo]
    patterns: List[str]  # Architectural patterns
    files: Dict[str, FileInfo]
    security_issues: List[str]


class ProjectAnalyzer:
    """Analyze project structure and dependencies."""
    
    # Build system detection
    BUILD_SYSTEM_MARKERS = {
        "maven": ["pom.xml"],
        "gradle": ["build.gradle", "build.gradle.kts"],
        "npm": ["package.json"],
        "poetry": ["pyproject.toml", "poetry.lock"],
        "pipenv": ["Pipfile", "Pipfile.lock"],
        "cargo": ["Cargo.toml"],
        "go": ["go.mod", "go.sum"],
        "dotnet": [".csproj", ".sln"],
        "maven-multimodule": ["pom.xml"],
    }
    
    ENTRY_POINT_PATTERNS = {
        "main.py",
        "app.py",
        "index.js",
        "index.ts",
        "main.go",
        "main.rs",
        "Program.cs",
        "Main.java",
    }
    
    ARCHITECTURAL_PATTERNS = [
        ("layered", ["layers", "controllers", "services", "models", "repositories"]),
        ("mvc", ["models", "views", "controllers"]),
        ("ddd", ["domain", "application", "infrastructure", "presentation"]),
        ("microservices", [".dockerfile", "docker-compose.yml"]),
        ("monolithic", ["src/", "lib/", "tests/"]),
        ("plugin", ["plugins/", "extensions/"]),
    ]
    
    def __init__(self, project_root: Path):
        """
        Initialize analyzer.
        
        Args:
            project_root: Root directory of project
        """
        self.project_root = project_root
        self.logger = get_logger(__name__)
        self.registry = LanguageRegistry()
    
    def analyze(self) -> ProjectMetadata:
        """
        Analyze complete project.
        
        Returns:
            ProjectMetadata with all findings
        """
        
        self.logger.info(f"Analyzing project: {self.project_root}")
        
        return ProjectMetadata(
            build_system=self._detect_build_system(),
            languages=self._detect_languages(),
            entry_points=self._find_entry_points(),
            dependencies=self._parse_dependencies(),
            patterns=self._detect_patterns(),
            files=self._analyze_files(),
            security_issues=self._scan_security(),
        )
    
    def save_metadata(self, metadata: ProjectMetadata, output_path: Optional[Path] = None):
        """Save metadata to JSON file."""
        
        if output_path is None:
            output_path = self.project_root / "project_metadata.json"
        
        # Convert to serializable format
        data = {
            "build_system": metadata.build_system,
            "languages": metadata.languages,
            "entry_points": metadata.entry_points,
            "dependencies": {
                name: asdict(dep) for name, dep in metadata.dependencies.items()
            },
            "patterns": metadata.patterns,
            "files": {
                path: asdict(info) for path, info in metadata.files.items()
            },
            "security_issues": metadata.security_issues,
        }
        
        output_path.write_text(json.dumps(data, indent=2))
        self.logger.info(f"✓ Saved metadata to {output_path}")
    
    def _detect_build_system(self) -> Optional[str]:
        """Detect project's build system."""
        
        for build_system, markers in self.BUILD_SYSTEM_MARKERS.items():
            for marker in markers:
                if (self.project_root / marker).exists():
                    self.logger.info(f"✓ Detected build system: {build_system}")
                    return build_system
        
        return None
    
    def _detect_languages(self) -> List[str]:
        """Detect programming languages used."""
        
        languages = set()
        
        for file_path in self.project_root.rglob("*"):
            if not file_path.is_file() or file_path.name.startswith('.'):
                continue
            
            language = self.registry.get_language_by_extension(file_path.suffix)
            if language:
                languages.add(language.value)
        
        return sorted(list(languages))
    
    def _find_entry_points(self) -> List[str]:
        """Find likely entry point files."""
        
        entry_points = []
        
        # Check root
        for marker in self.ENTRY_POINT_PATTERNS:
            path = self.project_root / marker
            if path.exists():
                entry_points.append(marker)
        
        # Check src/ subdirectory
        src_dir = self.project_root / "src"
        if src_dir.exists():
            for marker in self.ENTRY_POINT_PATTERNS:
                path = src_dir / marker
                if path.exists():
                    entry_points.append(f"src/{marker}")
        
        return entry_points
    
    def _parse_dependencies(self) -> Dict[str, DependencyInfo]:
        """Parse dependencies from manifests."""
        
        dependencies = {}
        
        # NPM/Yarn
        pkg_json = self.project_root / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text())
                for dep, version in data.get("dependencies", {}).items():
                    dependencies[dep] = DependencyInfo(
                        name=dep,
                        version=version,
                        scope="runtime",
                    )
                for dep, version in data.get("devDependencies", {}).items():
                    dependencies[dep] = DependencyInfo(
                        name=dep,
                        version=version,
                        scope="dev",
                    )
            except Exception as e:
                self.logger.warning(f"Error parsing package.json: {e}")
        
        # Python
        requirements = self.project_root / "requirements.txt"
        if requirements.exists():
            try:
                for line in requirements.read_text().splitlines():
                    if line.strip() and not line.startswith('#'):
                        # Parse "package==version" format
                        match = re.match(r"^([a-zA-Z0-9_-]+)(?:==|>=|<=|~=)?(.*)$", line)
                        if match:
                            name, version = match.groups()
                            dependencies[name] = DependencyInfo(
                                name=name,
                                version=version or None,
                                scope="runtime",
                            )
            except Exception as e:
                self.logger.warning(f"Error parsing requirements.txt: {e}")
        
        # Java/Maven
        pom_xml = self.project_root / "pom.xml"
        if pom_xml.exists():
            try:
                content = pom_xml.read_text()
                # Simple regex extraction (not full XML parsing to avoid deps)
                for match in re.finditer(
                    r"<dependency>\s*<groupId>(.*?)</groupId>\s*<artifactId>(.*?)</artifactId>",
                    content,
                ):
                    group_id, artifact_id = match.groups()
                    full_name = f"{group_id}:{artifact_id}"
                    dependencies[full_name] = DependencyInfo(
                        name=full_name,
                        scope="runtime",
                    )
            except Exception as e:
                self.logger.warning(f"Error parsing pom.xml: {e}")
        
        return dependencies
    
    def _detect_patterns(self) -> List[str]:
        """Detect architectural patterns."""
        
        patterns = []
        
        # Check for known directory structures
        for pattern_name, markers in self.ARCHITECTURAL_PATTERNS:
            if all((self.project_root / marker).exists() for marker in markers):
                patterns.append(pattern_name)
                self.logger.info(f"✓ Detected pattern: {pattern_name}")
        
        return patterns
    
    def _analyze_files(self) -> Dict[str, FileInfo]:
        """Analyze all source files."""
        
        files = {}
        
        # Skip large directories
        skip_dirs = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"}
        
        for file_path in self.project_root.rglob("*"):
            # Skip
            if not file_path.is_file():
                continue
            if any(part in skip_dirs for part in file_path.parts):
                continue
            if file_path.name.startswith('.'):
                continue
            
            language = self.registry.get_language_by_extension(file_path.suffix)
            if not language:
                continue
            
            # Relative path
            rel_path = str(file_path.relative_to(self.project_root))
            
            # Analyze file
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                files[rel_path] = FileInfo(
                    path=rel_path,
                    language=language.value,
                    imports=self._extract_imports(content, language),
                    exports=[],  # Field for future use
                    complexity=self._estimate_complexity(content),
                    is_test="_test" in rel_path or "test_" in rel_path,
                )
            except Exception as e:
                self.logger.debug(f"Error analyzing {rel_path}: {e}")
        
        return files
    
    def _scan_security(self) -> List[str]:
        """Scan for common security issues."""
        
        issues = []
        
        # Check for exposed secrets
        for file_path in self.project_root.rglob("*"):
            if not file_path.is_file() or file_path.name.startswith('.'):
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Check for hardcoded secrets
                if re.search(r"(password|api_key|secret|token)\s*=\s*['\"]", content, re.I):
                    issues.append(f"Possible hardcoded secret in {file_path.name}")
                
                # Check for SQL injection risk
                if re.search(r"SELECT.*\+\s*\w+|f['\"].*\{.*\}.*['\"]\s*SELECT", content):
                    issues.append(f"Possible SQL injection risk in {file_path.name}")
            
            except Exception:
                pass
        
        return issues
    
    @staticmethod
    def _extract_imports(content: str, language) -> List[str]:
        """Extract imports from source file."""
        
        imports = []
        language_val = language.value if hasattr(language, 'value') else str(language)
        
        if language_val == "python":
            for match in re.finditer(r"^(?:from|import)\s+([a-zA-Z0-9_.]+)", content, re.M):
                imports.append(match.group(1))
        
        elif language_val in ["javascript", "typescript"]:
            for match in re.finditer(r"^(?:import|require)\s+['\"]?([a-zA-Z0-9_./@-]+)", content, re.M):
                imports.append(match.group(1))
        
        elif language_val == "java":
            for match in re.finditer(r"^import\s+([a-zA-Z0-9_.]+);", content, re.M):
                imports.append(match.group(1))
        
        return list(set(imports))  # Deduplicate
    
    @staticmethod
    def _estimate_complexity(content: str) -> int:
        """Estimate cyclomatic complexity."""
        
        # Count control flow keywords (very rough estimate)
        complexity = 1
        for keyword in ['if', 'elif', 'else', 'for', 'while', 'try', 'except', 'case', 'switch']:
            complexity += content.count(keyword)
        
        return min(complexity, 20)  # Cap at 20
