"""
Semantic Compression using Multi-Pass LLM Summarization

Strategy:
1. Split large content into chunks
2. LLM summarizes each chunk (preserving type sigs, key info)
3. LLM summarizes summaries (recursive)
4. Result: Rich context in fewer tokens

Works without fine-tuning or external models.
"""

import logging
from typing import List, Optional, Dict, Any
import re

from core.llm import call_llm
from core.structured_logger import get_logger

logger = get_logger(__name__)


class SemanticCompressor:
    """Compress text using semantic summarization."""
    
    # Prompt templates for different content types
    CODE_SUMMARIZER_PROMPT = """
Analyze this code and provide a CONCISE 3-5 line summary covering:
1. Function/class names and signatures (PRESERVE EXACT NAMES)
2. Main purpose/responsibility
3. Key dependencies or inputs/outputs
4. Any important notes (async, error handling, etc)

Code:
{code}

SUMMARY (3-5 lines only):
"""
    
    FILE_SUMMARIZER_PROMPT = """
Summarize this entire file in 2-3 lines:
1. Type (module, class definitions, utilities, etc)
2. Key exports (function/class names)
3. Main purpose

File:
{file_content}

SUMMARY (2-3 lines only):
"""
    
    RECURSIVE_SUMMARIZER_PROMPT = """
You are given multiple summaries of related content. Create a BRIEF consolidated summary (max 3 lines):

Summaries to consolidate:
{summaries}

CONSOLIDATED SUMMARY (3 lines max):
"""
    
    def __init__(self, max_chunk_size: int = 2000):
        """
        Initialize compressor.
        
        Args:
            max_chunk_size: Characters per chunk before summarizing
        """
        self.max_chunk_size = max_chunk_size
        self.logger = get_logger(__name__)
    
    def compress_code(self, code: str, language: Optional[str] = None) -> str:
        """
        Compress source code using LLM.
        
        Args:
            code: Source code to compress
            language: Programming language (for better summarization)
        
        Returns:
            Compressed summary
        """
        
        self.logger.info(f"Compressing {len(code)} chars of {language or 'code'}")
        
        # For small code, just summarize directly
        if len(code) < self.max_chunk_size:
            return self._summarize_code_chunk(code)
        
        # For large code, chunk and summarize
        chunks = self._split_by_functions(code)
        chunk_summaries = []
        
        for i, chunk in enumerate(chunks):
            self.logger.debug(f"Summarizing chunk {i+1}/{len(chunks)}")
            summary = self._summarize_code_chunk(chunk)
            chunk_summaries.append(summary)
        
        # Merge summaries
        if len(chunk_summaries) > 1:
            return self._merge_summaries(chunk_summaries)
        
        return chunk_summaries[0] if chunk_summaries else code
    
    def compress_file(self, file_path: str, file_content: str) -> str:
        """
        Compress entire file.
        
        Args:
            file_path: Path to file (for context)
            file_content: File content
        
        Returns:
            Compressed summary
        """
        
        self.logger.info(f"Compressing file {file_path} ({len(file_content)} chars)")
        
        if len(file_content) < self.max_chunk_size:
            # Small file - summarize whole thing
            prompt = self.FILE_SUMMARIZER_PROMPT.format(
                file_content=file_content[:1000]  # First 1000 chars
            )
        else:
            # Large file - summarize first and last parts
            first_part = file_content[:self.max_chunk_size]
            last_part = file_content[-self.max_chunk_size:]
            middle_summary = f"... ({len(file_content) - 2*self.max_chunk_size} chars) ..."
            
            prompt = self.FILE_SUMMARIZER_PROMPT.format(
                file_content=f"{first_part}\n{middle_summary}\n{last_part}"
            )
        
        try:
            summary = call_llm(prompt, return_json=False)
            return summary.strip()
        except Exception as e:
            self.logger.warning(f"Compression failed: {e}")
            return file_content[:500] + "... [compression failed]"
    
    def compress_project_context(
        self,
        file_summaries: Dict[str, str],
    ) -> str:
        """
        Compress multiple file summaries into project overview.
        
        Args:
            file_summaries: {file_path: summary}
        
        Returns:
            Project-level summary
        """
        
        self.logger.info(f"Compressing {len(file_summaries)} file summaries")
        
        if len(file_summaries) <= 5:
            # Small project - combine all summaries
            combined = "\n".join(
                f"- {path}: {summary}"
                for path, summary in file_summaries.items()
            )
        else:
            # Large project - compress by directories
            by_dir = self._group_by_directory(file_summaries)
            combined = "\n".join(
                f"- {dir}/: {summaries[:100]}..."
                for dir, summaries in by_dir.items()
            )
        
        prompt = f"""
Analyze this project structure and create a BRIEF overview (3-5 lines):

Project Files:
{combined}

PROJECT OVERVIEW (3-5 lines):
1. Type/Purpose:
2. Key modules/components:
3. Dependencies/architecture:
"""
        
        try:
            overview = call_llm(prompt, return_json=False)
            return overview.strip()
        except Exception as e:
            self.logger.warning(f"Project compression failed: {e}")
            return combined[:500]
    
    # Private methods
    
    def _summarize_code_chunk(self, code: str) -> str:
        """Summarize a code chunk using LLM."""
        
        prompt = self.CODE_SUMMARIZER_PROMPT.format(code=code[:1500])
        
        try:
            summary = call_llm(prompt, return_json=False)
            return summary.strip()
        except Exception as e:
            self.logger.debug(f"Chunk summarization failed: {e}")
            # Fallback: extract just function signatures
            return self._extract_signatures(code)
    
    def _split_by_functions(self, code: str) -> List[str]:
        """
        Split code into chunks by function/class definitions.
        
        Preserves logical units.
        """
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for line in code.splitlines():
            current_chunk.append(line)
            current_size += len(line)
            
            # Split on function/class definitions if chunk is large
            if current_size > self.max_chunk_size and re.match(
                r"^(def|class|function|const|let|public|private)\s",
                line.strip()
            ):
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_size = len(line)
        
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        
        return chunks
    
    def _merge_summaries(self, summaries: List[str]) -> str:
        """Merge multiple summaries into one coherent summary."""
        
        if len(summaries) == 1:
            return summaries[0]
        
        prompt = self.RECURSIVE_SUMMARIZER_PROMPT.format(
            summaries="\n".join(f"{i+1}. {s}" for i, s in enumerate(summaries))
        )
        
        try:
            merged = call_llm(prompt, return_json=False)
            return merged.strip()
        except Exception as e:
            self.logger.warning(f"Merge failed: {e}")
            # Fallback: concatenate
            return " | ".join(summaries[:3])
    
    def _extract_signatures(self, code: str) -> str:
        """Extract function/class signatures as fallback."""
        
        lines = code.splitlines()
        signatures = []
        
        for line in lines:
            if re.match(r"^\s*(def|class|function|public|private|async)\s", line.strip()):
                signatures.append(line.strip())
        
        return "\n".join(signatures[:10]) if signatures else code[:200]
    
    @staticmethod
    def _group_by_directory(file_summaries: Dict[str, str]) -> Dict[str, str]:
        """Group file summaries by directory."""
        
        by_dir = {}
        for path, summary in file_summaries.items():
            dir_path = "/".join(path.split("/")[:-1])
            if dir_path not in by_dir:
                by_dir[dir_path] = []
            by_dir[dir_path].append(summary)
        
        return {
            dir: " | ".join(sums)
            for dir, sums in by_dir.items()
        }
