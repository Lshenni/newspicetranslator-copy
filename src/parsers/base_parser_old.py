"""Base parser class for SPICE model formats.

This module provides the abstract base class for all SPICE format parsers,
defining the common interface and functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Abstract base class for SPICE model parsers.

    This class defines the interface that all SPICE format parsers must implement.
    """

    def __init__(self, file_path: Path):
        """Initialize the parser.

        Args:
            file_path: Path to the SPICE model file to parse
        """
        self.file_path = file_path
        self.content: Optional[str] = None
        self.models: List[Dict[str, Any]] = []
        self._load_file()

    def _load_file(self) -> None:
        """Load the SPICE file content."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
        except UnicodeDecodeError:
            # Try with latin-1 encoding for some SPICE files
            try:
                with open(self.file_path, 'r', encoding='latin-1') as f:
                    self.content = f.read()
            except Exception as e:
                logger.error(f"Failed to read file {self.file_path}: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to read file {self.file_path}: {e}")
            raise

    @staticmethod
    def detect_format(file_path: Path, content: Optional[str] = None) -> str:
        """Detect the SPICE format of a file based on content analysis.

        Args:
            file_path: Path to the SPICE file
            content: File content (optional, will be read if not provided)

        Returns:
            Detected format: 'spectre', 'hspice', 'ngspice', or 'generic'
        """
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
                except Exception:
                    return 'generic'
            except Exception:
                return 'generic'

        content_lower = content.lower()

        # Check file extension first
        suffix = file_path.suffix.lower()

        # Spectre indicators (highest priority)
        if suffix == '.scs':
            return 'spectre'
        if 'simulator lang = spectre' in content_lower:
            return 'spectre'
        if 'ahdl_include' in content_lower:
            return 'spectre'
        if re.search(r'\bsection\s+\w+', content_lower):
            return 'spectre'

        # HSPICE indicators
        if suffix in ['.sp', '.lib', '.inc']:
            # Check for HSPICE-specific syntax
            if '.model' in content_lower and '.lib' in content_lower:
                return 'hspice'
            if re.search(r'\.lib\s+\w+', content_lower):
                return 'hspice'

        # ngspice indicators
        if '.model' in content_lower and '.end' in content_lower:
            # ngspice typically uses different parameter sets
            if any(param in content_lower for param in ['level', 'tnom', 'tox']):
                return 'ngspice'

        # Generic SPICE (catch-all)
        if '.model' in content_lower or '.include' in content_lower:
            return 'generic'

        # Default fallback
        return 'generic'

    def _load_file_with_includes(self, max_depth: int = 5, processed_files: set = None) -> str:
        """Load file content with include resolution.

        Args:
            max_depth: Maximum include depth to prevent infinite recursion
            processed_files: Set of already processed files

        Returns:
            Combined content from main file and includes
        """
        if processed_files is None:
            processed_files = set()

        if str(self.file_path) in processed_files:
            logger.warning(f"Circular include detected: {self.file_path}")
            return ""

        if max_depth <= 0:
            logger.warning(f"Maximum include depth exceeded for {self.file_path}")
            return ""

        processed_files.add(str(self.file_path))

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(self.file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Failed to read file {self.file_path}: {e}")
                return ""
        except Exception as e:
            logger.error(f"Failed to read file {self.file_path}: {e}")
            return ""

        # Process includes
        lines = content.split('\n')
        processed_content = []

        for line in lines:
            processed_content.append(line)

            # Check for include statements
            stripped = line.strip().lower()
            if stripped.startswith('.include ') or stripped.startswith('.inc ') or \
               stripped.startswith('include ') or stripped.startswith('ahdl_include '):

                include_path = self._extract_include_path(line)
                if include_path:
                    resolved_path = self._resolve_include_path(include_path)
                    if resolved_path and resolved_path.exists():
                        logger.info(f"Following include: {resolved_path}")
                        # Create a temporary parser to load included content
                        temp_parser = self.__class__(resolved_path)
                        included_content = temp_parser._load_file_with_includes(
                            max_depth - 1, processed_files.copy()
                        )
                        if included_content:
                            # Add included content as comments to preserve line numbers
                            processed_content.append(f"* BEGIN INCLUDE: {resolved_path}")
                            processed_content.extend(included_content.split('\n'))
                            processed_content.append(f"* END INCLUDE: {resolved_path}")
                    else:
                        logger.warning(f"Could not resolve include path: {include_path}")

        return '\n'.join(processed_content)

    def _extract_include_path(self, line: str) -> Optional[str]:
        """Extract include path from include statement.

        Args:
            line: Include statement line

        Returns:
            Extracted path or None
        """
        # Handle various include formats:
        # .include "path"
        # .include 'path'
        # .include path
        # include "path"
        # ahdl_include "path"

        import re
        patterns = [
            r'\.include\s+["\']([^"\']+)["\']',
            r'\.include\s+(\S+)',
            r'\.inc\s+["\']([^"\']+)["\']',
            r'\.inc\s+(\S+)',
            r'include\s+["\']([^"\']+)["\']',
            r'include\s+(\S+)',
            r'ahdl_include\s+["\']([^"\']+)["\']',
            r'ahdl_include\s+(\S+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _resolve_include_path(self, include_path: str) -> Optional[Path]:
        """Resolve include path relative to current file.

        Args:
            include_path: Include path from statement

        Returns:
            Resolved absolute path or None
        """
        # Try relative to current file directory
        relative_path = self.file_path.parent / include_path
        if relative_path.exists():
            return relative_path

        # Try relative to project root
        project_root = Path(__file__).parent.parent.parent
        project_path = project_root / include_path
        if project_path.exists():
            return project_path

        # Try in tools directory
        tools_path = project_root / "tools" / include_path
        if tools_path.exists():
            return tools_path

        # Try in models directory
        models_path = project_root / "tools" / "spice-libraries" / "private-models" / include_path
        if models_path.exists():
            return models_path

        # Try relative to current file's parent directories (for nested includes)
        current_dir = self.file_path.parent
        for _ in range(3):  # Check up to 3 levels up
            test_path = current_dir / include_path
            if test_path.exists():
                return test_path
            current_dir = current_dir.parent

        # Try with common PDK include patterns
        # Handle relative paths like "../../../cells/..."
        if include_path.startswith('../') or include_path.startswith('cells/'):
            # Try relative to models directory
            for models_dir in (project_root / "tools" / "spice-libraries" / "private-models").iterdir():
                if models_dir.is_dir():
                    test_path = models_dir / include_path
                    if test_path.exists():
                        return test_path

        return None

    @abstractmethod
    def parse(self, follow_includes: bool = False) -> List[Dict[str, Any]]:
        """Parse the SPICE file and extract model information.

        Args:
            follow_includes: Whether to follow include statements and parse included files

        Returns:
            List of model dictionaries containing parameters and metadata
        """
        pass

    @abstractmethod
    def get_format_name(self) -> str:
        """Get the name of the SPICE format this parser handles.

        Returns:
            Format name (e.g., 'spectre', 'hspice', 'ngspice')
        """
        pass

    def extract_model_name(self, model_line: str) -> Optional[str]:
        """Extract model name from a model definition line.

        Args:
            model_line: Line containing model definition

        Returns:
            Model name if found, None otherwise
        """
        # Common pattern: .model <name> <type>
        import re
        match = re.search(r'\.model\s+(\w+)', model_line, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def extract_parameters(self, param_string: str) -> Dict[str, Any]:
        """Extract parameters from a parameter string.

        Args:
            param_string: String containing parameter definitions

        Returns:
            Dictionary of parameter names to values
        """
        parameters = {}
        import re

        # Split by whitespace and = signs, handling quoted strings
        # This is a simplified version - real parsers need more sophisticated logic
        param_pattern = r'(\w+)\s*=\s*([^=\s]+(?:\s+[^=\s]+)*?)(?=\s+\w+\s*=|$)'
        matches = re.findall(param_pattern, param_string, re.IGNORECASE)

        for param_name, param_value in matches:
            param_name = param_name.strip()
            param_value = param_value.strip()

            # Try to convert to numeric if possible
            try:
                # Handle scientific notation and units
                if 'e' in param_value.lower() or '.' in param_value:
                    parameters[param_name.lower()] = float(param_value)
                else:
                    parameters[param_name.lower()] = float(param_value)
            except ValueError:
                parameters[param_name.lower()] = param_value

        return parameters
