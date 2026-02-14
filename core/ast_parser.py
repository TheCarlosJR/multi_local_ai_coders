"""
Unified AST Parser using Tree-Sitter

Provides consistent AST parsing across all supported languages.
Tree-Sitter: https://tree-sitter.github.io/tree-sitter/

Installation:
    pip install tree-sitter tree-sitter-languages
"""

import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from functools import lru_cache

try:
    from tree_sitter import Language, Parser, Node
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

from core.language_registry import Language as ProgrammingLanguage, LanguageRegistry

logger = logging.getLogger(__name__)


class TreeSitterManager:
    """Manages Tree-Sitter parsers for multiple languages."""
    
    _instance = None
    _parsers: Dict[str, Parser] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        if not TREE_SITTER_AVAILABLE:
            logger.warning("Tree-sitter not available. Install with: pip install tree-sitter tree-sitter-languages")
            return
        
        self.logger = logging.getLogger(__name__)
        self.registry = LanguageRegistry()
        self._initialize_parsers()
    
    def _initialize_parsers(self):
        """Initialize Tree-Sitter parsers for all languages."""
        
        try:
            from tree_sitter_languages import get_language, get_parser
        except ImportError:
            self.logger.error("tree-sitter-languages package required")
            return
        
        # Map of Tree-Sitter language names
        ts_languages = [
            "python", "typescript", "javascript", "java", "go", "rust",
            "cpp", "c_sharp", "ruby", "php", "bash", "dockerfile"
        ]
        
        for ts_lang in ts_languages:
            try:
                parser = get_parser(ts_lang)
                self._parsers[ts_lang] = parser
                self.logger.debug(f"✓ Initialized Tree-Sitter parser for {ts_lang}")
            except Exception as e:
                self.logger.warning(f"Could not initialize {ts_lang}: {e}")
    
    def get_parser(self, language: ProgrammingLanguage) -> Optional[Parser]:
        """Get parser for programming language."""
        
        if not TREE_SITTER_AVAILABLE:
            return None
        
        config = self.registry.get_config(language)
        if not config:
            return None
        
        return self._parsers.get(config.tree_sitter_language)


class ASTParser:
    """Parse source code into AST."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ts_manager = TreeSitterManager()
        self.registry = LanguageRegistry()
    
    def parse_file(self, file_path: Path, language: Optional[ProgrammingLanguage] = None) -> Optional[Node]:
        """
        Parse file and return AST root node.
        
        Args:
            file_path: Path to source file
            language: Programming language (auto-detect if None)
        
        Returns:
            Tree-Sitter Node (root of AST)
        """
        
        try:
            content = file_path.read_text(encoding="utf-8")
            return self.parse_string(content, language or self._detect_language(file_path))
        except Exception as e:
            self.logger.error(f"Error parsing {file_path}: {e}")
            return None
    
    def parse_string(self, code: str, language: ProgrammingLanguage) -> Optional[Node]:
        """Parse code string and return AST."""
        
        if not TREE_SITTER_AVAILABLE:
            self.logger.debug("Tree-sitter not available, skipping parsing")
            return None
        
        parser = self.ts_manager.get_parser(language)
        if not parser:
            self.logger.warning(f"No parser for {language}")
            return None
        
        try:
            tree = parser.parse(code.encode('utf-8'))
            return tree.root_node
        except Exception as e:
            self.logger.error(f"Error parsing {language} code: {e}")
            return None
    
    def extract_functions(self, root_node: Optional[Node], language: ProgrammingLanguage) -> List[Dict[str, Any]]:
        """Extract function/method definitions from AST."""
        
        if not root_node:
            return []
        
        functions = []
        
        # Query patterns per language
        queries = {
            ProgrammingLanguage.PYTHON: [
                "function_definition",
                "async_function_definition"
            ],
            ProgrammingLanguage.TYPESCRIPT: [
                "function_declaration",
                "method_definition"
            ],
            ProgrammingLanguage.JAVASCRIPT: [
                "function_declaration",
                "method_definition"
            ],
            ProgrammingLanguage.JAVA: [
                "method_declaration"
            ],
            ProgrammingLanguage.GO: [
                "function_declaration",
                "method_declaration"
            ],
            ProgrammingLanguage.RUST: [
                "function_item",
                "impl_item"
            ],
        }
        
        patterns = queries.get(language, ["function_declaration"])
        
        def walk(node: Node):
            if node.type in patterns:
                functions.append({
                    "name": self._extract_name(node),
                    "start_line": node.start_point[0],
                    "end_line": node.end_point[0],
                    "type": node.type,
                })
            
            for child in node.children:
                walk(child)
        
        walk(root_node)
        return functions
    
    def extract_classes(self, root_node: Optional[Node], language: ProgrammingLanguage) -> List[Dict[str, Any]]:
        """Extract class definitions from AST."""
        
        if not root_node:
            return []
        
        classes = []
        
        queries = {
            ProgrammingLanguage.PYTHON: ["class_definition"],
            ProgrammingLanguage.TYPESCRIPT: ["class_declaration"],
            ProgrammingLanguage.JAVASCRIPT: ["class_declaration"],
            ProgrammingLanguage.JAVA: ["class_declaration"],
            ProgrammingLanguage.GO: ["type_spec"],
            ProgrammingLanguage.RUST: ["struct_item"],
        }
        
        patterns = queries.get(language, ["class_declaration"])
        
        def walk(node: Node):
            if node.type in patterns:
                classes.append({
                    "name": self._extract_name(node),
                    "start_line": node.start_point[0],
                    "end_line": node.end_point[0],
                    "type": node.type,
                })
            
            for child in node.children:
                walk(child)
        
        walk(root_node)
        return classes
    
    def extract_imports(self, root_node: Optional[Node], language: ProgrammingLanguage) -> List[str]:
        """Extract import statements from AST."""
        
        if not root_node:
            return []
        
        imports = []
        
        queries = {
            ProgrammingLanguage.PYTHON: ["import_statement", "from_import_statement"],
            ProgrammingLanguage.TYPESCRIPT: ["import_statement"],
            ProgrammingLanguage.JAVASCRIPT: ["import_statement"],
            ProgrammingLanguage.JAVA: ["import_declaration"],
            ProgrammingLanguage.GO: ["import_declaration"],
            ProgrammingLanguage.RUST: ["use_declaration"],
        }
        
        patterns = queries.get(language, ["import_statement"])
        
        def walk(node: Node):
            if node.type in patterns:
                import_text = self._extract_text(node)
                if import_text:
                    imports.append(import_text)
            
            for child in node.children:
                walk(child)
        
        walk(root_node)
        return imports
    
    def get_file_summary(self, file_path: Path) -> Dict[str, Any]:
        """Get high-level summary of file structure."""
        
        language = self._detect_language(file_path)
        if not language:
            return {}
        
        root_node = self.parse_file(file_path, language)
        
        return {
            "language": language.value,
            "file": str(file_path),
            "functions": self.extract_functions(root_node, language),
            "classes": self.extract_classes(root_node, language),
            "imports": self.extract_imports(root_node, language),
            "lines_of_code": self._count_lines(file_path),
        }
    
    @staticmethod
    def _detect_language(file_path: Path) -> Optional[ProgrammingLanguage]:
        """Detect language from file extension."""
        registry = LanguageRegistry()
        return registry.get_language_by_extension(file_path.suffix)
    
    @staticmethod
    def _extract_name(node: Node) -> str:
        """Extract name from function/class node."""
        for child in node.children:
            if child.type in ["identifier", "property_identifier"]:
                return child.text.decode('utf-8')
        return "unknown"
    
    @staticmethod
    def _extract_text(node: Node) -> str:
        """Extract text content from node."""
        try:
            return node.text.decode('utf-8')
        except (UnicodeDecodeError, AttributeError):
            return ""
    
    @staticmethod
    def _count_lines(file_path: Path) -> int:
        """Count lines of code."""
        try:
            return len(file_path.read_text(encoding='utf-8').splitlines())
        except (OSError, UnicodeDecodeError):
            return 0
