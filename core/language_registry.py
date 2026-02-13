"""
Language Registry - Multi-Language Support Configuration

Suporta detecção automática de linguagens e configuração de ferramentas específicas
baseado em extensão de arquivo e estrutura do projeto.

Linguagens Suportadas:
- Python, TypeScript/JavaScript, Java, Go, Rust, C/C++, C#, Ruby, PHP, Kotlin, R, Julia, Shell, Dockerfile
"""

from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class Language(str, Enum):
    """Supported programming languages."""
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    RUBY = "ruby"
    PHP = "php"
    KOTLIN = "kotlin"
    R = "r"
    JULIA = "julia"
    SHELL = "shell"
    DOCKERFILE = "dockerfile"
    YAML = "yaml"
    JSON = "json"
    SQL = "sql"


@dataclass
class LanguageConfig:
    """Configuration for a language."""
    language: Language
    file_extensions: Set[str]
    tree_sitter_language: str  # Name in tree-sitter library
    linters: List[str] = field(default_factory=list)
    type_checkers: List[str] = field(default_factory=list)
    formatters: List[str] = field(default_factory=list)
    security_scanners: List[str] = field(default_factory=list)
    lsp_command: Optional[List[str]] = None  # Command to start LSP server
    build_commands: List[str] = field(default_factory=list)
    test_commands: List[str] = field(default_factory=list)
    package_managers: List[str] = field(default_factory=list)


class LanguageRegistry:
    """Registry of supported languages and their tools."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.logger = logging.getLogger(__name__)
        self.registry: Dict[Language, LanguageConfig] = {}
        self._setup_languages()
    
    def _setup_languages(self):
        """Initialize all supported languages."""
        
        configs = [
            LanguageConfig(
                language=Language.PYTHON,
                file_extensions={".py"},
                tree_sitter_language="python",
                linters=["pylint", "flake8"],
                type_checkers=["mypy"],
                formatters=["black", "autopep8"],
                security_scanners=["bandit"],
                build_commands=["python setup.py build"],
                test_commands=["pytest", "unittest"],
                package_managers=["pip", "poetry", "pipenv"],
            ),
            LanguageConfig(
                language=Language.TYPESCRIPT,
                file_extensions={".ts", ".tsx"},
                tree_sitter_language="typescript",
                linters=["eslint"],
                type_checkers=["tsc"],
                formatters=["prettier"],
                security_scanners=["snyk", "sonarjs"],
                lsp_command=["typescript-language-server", "--stdio"],
                build_commands=["tsc"],
                test_commands=["npm test", "yarn test"],
                package_managers=["npm", "yarn", "pnpm"],
            ),
            LanguageConfig(
                language=Language.JAVASCRIPT,
                file_extensions={".js", ".jsx", ".mjs"},
                tree_sitter_language="javascript",
                linters=["eslint"],
                type_checkers=[],  # JSDoc only
                formatters=["prettier"],
                security_scanners=["snyk"],
                build_commands=["npm run build"],
                test_commands=["npm test", "jest"],
                package_managers=["npm", "yarn"],
            ),
            LanguageConfig(
                language=Language.JAVA,
                file_extensions={".java"},
                tree_sitter_language="java",
                linters=["checkstyle"],
                type_checkers=["javac"],
                formatters=["google-java-format"],
                security_scanners=["spotbugs", "semgrep"],
                build_commands=["mvn compile", "gradle build"],
                test_commands=["mvn test", "gradle test"],
                package_managers=["maven", "gradle"],
            ),
            LanguageConfig(
                language=Language.GO,
                file_extensions={".go"},
                tree_sitter_language="go",
                linters=["golint", "go vet"],
                type_checkers=["go build"],
                formatters=["gofmt"],
                security_scanners=["gosec"],
                lsp_command=["gopls", "serve"],
                build_commands=["go build"],
                test_commands=["go test"],
                package_managers=["go get"],
            ),
            LanguageConfig(
                language=Language.RUST,
                file_extensions={".rs"},
                tree_sitter_language="rust",
                linters=["clippy"],
                type_checkers=["rustc"],
                formatters=["rustfmt"],
                security_scanners=["cargo audit"],
                lsp_command=["rust-analyzer"],
                build_commands=["cargo build"],
                test_commands=["cargo test"],
                package_managers=["cargo"],
            ),
            LanguageConfig(
                language=Language.CPP,
                file_extensions={".cpp", ".cc", ".cxx", ".h", ".hpp"},
                tree_sitter_language="cpp",
                linters=["clang-tidy"],
                type_checkers=["clang++"],
                formatters=["clang-format"],
                security_scanners=["semgrep"],
                lsp_command=["clangd"],
                build_commands=["g++ -c", "clang++ -c"],
                test_commands=["ctest"],
                package_managers=["conan"],
            ),
            LanguageConfig(
                language=Language.CSHARP,
                file_extensions={".cs"},
                tree_sitter_language="c_sharp",
                linters=["StyleCop"],
                type_checkers=["csc"],
                formatters=["dotnet format"],
                security_scanners=["sonarqube"],
                lsp_command=["omnisharp"],
                build_commands=["dotnet build"],
                test_commands=["dotnet test"],
                package_managers=["nuget", "dotnet"],
            ),
            LanguageConfig(
                language=Language.RUBY,
                file_extensions={".rb"},
                tree_sitter_language="ruby",
                linters=["rubocop"],
                type_checkers=[],
                formatters=["rubocop --auto-correct"],
                security_scanners=["bundler-audit"],
                lsp_command=["solargraph", "stdio"],
                build_commands=[],
                test_commands=["rspec", "rake test"],
                package_managers=["gem", "bundler"],
            ),
            LanguageConfig(
                language=Language.PHP,
                file_extensions={".php"},
                tree_sitter_language="php",
                linters=["phpcs"],
                type_checkers=["phpstan"],
                formatters=["php-cs-fixer"],
                security_scanners=["psalm"],
                lsp_command=["php-language-server"],
                build_commands=[],
                test_commands=["phpunit"],
                package_managers=["composer"],
            ),
            LanguageConfig(
                language=Language.SHELL,
                file_extensions={".sh", ".bash"},
                tree_sitter_language="bash",
                linters=["shellcheck"],
                type_checkers=[],
                formatters=["shfmt"],
                security_scanners=["shellcheck"],
                build_commands=[],
                test_commands=["bats"],
                package_managers=[],
            ),
            LanguageConfig(
                language=Language.DOCKERFILE,
                file_extensions={"dockerfile", "Dockerfile"},
                tree_sitter_language="dockerfile",
                linters=["hadolint"],
                type_checkers=[],
                formatters=[],
                security_scanners=["trivy"],
                build_commands=["docker build"],
                test_commands=[],
                package_managers=[],
            ),
        ]
        
        for config in configs:
            self.registry[config.language] = config
        
        self.logger.info(f"✓ Registered {len(configs)} languages")
    
    def get_language_by_extension(self, extension: str) -> Optional[Language]:
        """Get language from file extension."""
        extension = extension.lower()
        for language, config in self.registry.items():
            if extension in config.file_extensions:
                return language
        return None
    
    def get_config(self, language: Language) -> Optional[LanguageConfig]:
        """Get configuration for a language."""
        return self.registry.get(language)
    
    def is_supported(self, language: Language) -> bool:
        """Check if language is supported."""
        return language in self.registry
    
    def get_all_extensions(self) -> Dict[str, Language]:
        """Get map of all extensions to languages."""
        ext_map = {}
        for language, config in self.registry.items():
            for ext in config.file_extensions:
                ext_map[ext] = language
        return ext_map
    
    def get_linters(self, language: Language) -> List[str]:
        """Get linters for language."""
        config = self.get_config(language)
        return config.linters if config else []
    
    def get_type_checkers(self, language: Language) -> List[str]:
        """Get type checkers for language."""
        config = self.get_config(language)
        return config.type_checkers if config else []
    
    def get_security_scanners(self, language: Language) -> List[str]:
        """Get security scanners for language."""
        config = self.get_config(language)
        return config.security_scanners if config else []
