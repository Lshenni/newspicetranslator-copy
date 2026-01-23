"""
Abstract base parser for SPICE formats.

All format-specific parsers inherit from this class and implement
parse_to_ir() to convert their format to the universal IR.

Compliance: CONSTRAINTS.md
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Set
from pathlib import Path
import logging

from ..ir.model_ir import ModelIR

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """
    Abstract base class for all SPICE format parsers.
    
    Parsers convert format-specific model files to universal IR representation.
    Each format (Spectre, HSPICE, ngspice) has its own parser implementation.
    """
    
    def __init__(self, file_path: Path) -> None:
        """
        Initialize parser with input file.
        
        Args:
            file_path: Path to SPICE model file
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.file_path = file_path
        self.content = self._load_file()
        self.included_files: Set[Path] = set()
        
        logger.info(f"Initialized {self.get_format_name()} parser for {file_path}")
    
    def _load_file(self) -> str:
        """
        Load file content with error handling.
        
        Returns:
            File content as string
            
        Raises:
            IOError: If file cannot be read
        """
        try:
            content = self.file_path.read_text(encoding='utf-8')
            logger.debug(f"Loaded {len(content)} characters from {self.file_path}")
            return content
        except UnicodeDecodeError:
            # Try with latin-1 encoding as fallback
            logger.warning(f"UTF-8 decode failed, trying latin-1 for {self.file_path}")
            return self.file_path.read_text(encoding='latin-1')
    
    @abstractmethod
    def get_format_name(self) -> str:
        """
        Get the format name handled by this parser.
        
        Returns:
            Format name ('spectre', 'hspice', 'ngspice')
        """
        pass
    
    @abstractmethod
    def parse_to_ir(self, follow_includes: bool = False) -> List[ModelIR]:
        """
        Parse file content and convert to IR representation.
        
        This is the main method that subclasses must implement.
        
        Args:
            follow_includes: Whether to recursively parse .include files
            
        Returns:
            List of ModelIR objects extracted from file
            
        Raises:
            ValueError: If file content is invalid
            RuntimeError: If parsing fails
        """
        pass
    
    def get_included_files(self) -> Set[Path]:
        """
        Get set of all included files discovered during parsing.
        
        Returns:
            Set of Path objects for included files
        """
        return self.included_files.copy()
    
    def _resolve_include_path(self, include_path: str) -> Optional[Path]:
        """
        Resolve include file path relative to current file.
        
        Args:
            include_path: Include path from .include directive
            
        Returns:
            Resolved absolute Path, or None if not found
        """
        # Try relative to current file
        base_dir = self.file_path.parent
        resolved = base_dir / include_path
        
        if resolved.exists():
            return resolved.resolve()
        
        # Try as absolute path
        abs_path = Path(include_path)
        if abs_path.exists():
            return abs_path.resolve()
        
        logger.warning(f"Include file not found: {include_path}")
        return None
    
    def validate_content(self) -> bool:
        """
        Basic validation of file content.
        
        Returns:
            True if content appears valid, False otherwise
        """
        if not self.content or len(self.content.strip()) == 0:
            logger.error("File content is empty")
            return False
        
        return True
    
    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"{self.__class__.__name__}(file='{self.file_path.name}')"
