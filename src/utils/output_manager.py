"""
Output file organization and naming utilities.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional
import shutil


class OutputManager:
    """
    Manages output file organization and naming.
    
    Provides consistent naming and folder structure for translated files.
    """
    
    def __init__(self, base_dir: Path = None):
        """
        Initialize output manager.
        
        Args:
            base_dir: Base output directory (default: ./output)
        """
        if base_dir is None:
            base_dir = Path.cwd() / 'output'
        
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def get_translation_dir(
        self,
        source_format: str,
        target_format: str
    ) -> Path:
        """
        Get directory for translations.
        
        Args:
            source_format: Source format (spectre, hspice, ngspice)
            target_format: Target format
        
        Returns:
            Path to translation directory
        
        Example:
            >>> manager.get_translation_dir('spectre', 'ngspice')
            Path('output/spectre_to_ngspice')
        """
        dir_name = f"{source_format}_to_{target_format}"
        output_dir = self.base_dir / dir_name
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    
    def get_output_path(
        self,
        input_file: Path,
        source_format: str,
        target_format: str,
        suffix: str = None
    ) -> Path:
        """
        Get organized output path for translation.
        
        Args:
            input_file: Original input file
            source_format: Source format
            target_format: Target format
            suffix: Optional suffix (e.g., '_validated')
        
        Returns:
            Path for output file with correct extension
        
        Example:
            >>> manager.get_output_path(
            ...     Path('models.scs'),
            ...     'spectre',
            ...     'ngspice'
            ... )
            Path('output/spectre_to_ngspice/models.lib')
        """
        # Get translation directory
        output_dir = self.get_translation_dir(source_format, target_format)
        
        # Determine file extension
        extensions = {
            'spectre': 'scs',
            'hspice': 'sp',
            'ngspice': 'lib'
        }
        ext = extensions[target_format.lower()]
        
        # Build filename
        base_name = input_file.stem
        if suffix:
            base_name = f"{base_name}{suffix}"
        
        filename = f"{base_name}.{ext}"
        
        return output_dir / filename
    
    def get_report_path(
        self,
        report_type: str,
        format: str = 'json'
    ) -> Path:
        """
        Get path for report file with timestamp.
        
        Args:
            report_type: Type of report (translation, roundtrip, batch)
            format: Report format (json, txt, html)
        
        Returns:
            Path for report file
        
        Example:
            >>> manager.get_report_path('translation')
            Path('output/reports/translation_report_2026-01-23_14-30-00.json')
        """
        reports_dir = self.base_dir / 'reports'
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"{report_type}_report_{timestamp}.{format}"
        
        return reports_dir / filename
    
    def get_intermediate_dir(self) -> Path:
        """Get directory for intermediate/temp files."""
        intermediate_dir = self.base_dir / 'intermediate'
        intermediate_dir.mkdir(parents=True, exist_ok=True)
        return intermediate_dir
    
    def clean_intermediate(self):
        """Clean up intermediate/temp files."""
        intermediate_dir = self.get_intermediate_dir()
        if intermediate_dir.exists():
            shutil.rmtree(intermediate_dir)
            intermediate_dir.mkdir()
    
    def get_batch_summary_path(self) -> Path:
        """Get path for batch processing summary."""
        return self.get_report_path('batch_summary', 'json')
    
    def organize_existing_files(
        self,
        source_dir: Path,
        source_format: str,
        target_format: str
    ):
        """
        Organize existing translated files into proper structure.
        
        Args:
            source_dir: Directory containing translated files
            source_format: Source format
            target_format: Target format
        
        Returns:
            Number of files organized
        
        Example:
            >>> manager.organize_existing_files(
            ...     Path('/tmp/translations'),
            ...     'spectre',
            ...     'ngspice'
            ... )
            5
        """
        target_dir = self.get_translation_dir(source_format, target_format)
        
        extensions = {
            'spectre': '.scs',
            'hspice': '.sp',
            'ngspice': '.lib'
        }
        ext = extensions[target_format]
        
        # Move matching files
        moved_count = 0
        for file in source_dir.glob(f"*{ext}"):
            target_path = target_dir / file.name
            shutil.copy2(file, target_path)
            moved_count += 1
        
        print(f"Organized {moved_count} files into {target_dir}")
        
        return moved_count
