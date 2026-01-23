"""
IR serialization and deserialization utilities.

Provides JSON and YAML serialization for ModelIR objects,
enabling persistence and interchange.

Compliance: CONSTRAINTS.md
"""

from typing import List, Dict, Any, Union
from pathlib import Path
import json
import logging

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logging.warning("PyYAML not available, YAML support disabled")

from .model_ir import ModelIR

logger = logging.getLogger(__name__)


class IRSerializer:
    """
    Serialization utilities for ModelIR objects.
    
    Supports JSON and YAML formats for IR persistence and interchange.
    """
    
    @staticmethod
    def to_json(models: Union[ModelIR, List[ModelIR]], pretty: bool = True) -> str:
        """
        Serialize ModelIR to JSON string.
        
        Args:
            models: Single ModelIR or list of ModelIR objects
            pretty: Whether to use pretty formatting
            
        Returns:
            JSON string representation
        """
        if isinstance(models, ModelIR):
            data = models.to_dict()
        else:
            data = [m.to_dict() for m in models]
        
        if pretty:
            return json.dumps(data, indent=2, sort_keys=False)
        return json.dumps(data)
    
    @staticmethod
    def from_json(json_str: str) -> Union[ModelIR, List[ModelIR]]:
        """
        Deserialize ModelIR from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            ModelIR or list of ModelIR objects
        """
        data = json.loads(json_str)
        
        if isinstance(data, dict):
            return ModelIR.from_dict(data)
        elif isinstance(data, list):
            return [ModelIR.from_dict(d) for d in data]
        else:
            raise ValueError(f"Invalid JSON structure: expected dict or list, got {type(data)}")
    
    @staticmethod
    def to_json_file(
        models: Union[ModelIR, List[ModelIR]],
        file_path: Path,
        pretty: bool = True
    ) -> None:
        """
        Write ModelIR to JSON file.
        
        Args:
            models: ModelIR object(s) to serialize
            file_path: Output file path
            pretty: Whether to use pretty formatting
        """
        json_str = IRSerializer.to_json(models, pretty=pretty)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json_str, encoding='utf-8')
        logger.info(f"Wrote IR to JSON file: {file_path}")
    
    @staticmethod
    def from_json_file(file_path: Path) -> Union[ModelIR, List[ModelIR]]:
        """
        Read ModelIR from JSON file.
        
        Args:
            file_path: Input file path
            
        Returns:
            ModelIR or list of ModelIR objects
        """
        json_str = file_path.read_text(encoding='utf-8')
        models = IRSerializer.from_json(json_str)
        logger.info(f"Loaded IR from JSON file: {file_path}")
        return models
    
    @staticmethod
    def to_yaml(models: Union[ModelIR, List[ModelIR]]) -> str:
        """
        Serialize ModelIR to YAML string.
        
        Args:
            models: Single ModelIR or list of ModelIR objects
            
        Returns:
            YAML string representation
            
        Raises:
            ImportError: If PyYAML is not available
        """
        if not YAML_AVAILABLE:
            raise ImportError("PyYAML not available. Install with: pip install pyyaml")
        
        if isinstance(models, ModelIR):
            data = models.to_dict()
        else:
            data = [m.to_dict() for m in models]
        
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
    
    @staticmethod
    def from_yaml(yaml_str: str) -> Union[ModelIR, List[ModelIR]]:
        """
        Deserialize ModelIR from YAML string.
        
        Args:
            yaml_str: YAML string representation
            
        Returns:
            ModelIR or list of ModelIR objects
            
        Raises:
            ImportError: If PyYAML is not available
        """
        if not YAML_AVAILABLE:
            raise ImportError("PyYAML not available. Install with: pip install pyyaml")
        
        data = yaml.safe_load(yaml_str)
        
        if isinstance(data, dict):
            return ModelIR.from_dict(data)
        elif isinstance(data, list):
            return [ModelIR.from_dict(d) for d in data]
        else:
            raise ValueError(f"Invalid YAML structure: expected dict or list, got {type(data)}")
    
    @staticmethod
    def to_yaml_file(models: Union[ModelIR, List[ModelIR]], file_path: Path) -> None:
        """
        Write ModelIR to YAML file.
        
        Args:
            models: ModelIR object(s) to serialize
            file_path: Output file path
            
        Raises:
            ImportError: If PyYAML is not available
        """
        yaml_str = IRSerializer.to_yaml(models)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(yaml_str, encoding='utf-8')
        logger.info(f"Wrote IR to YAML file: {file_path}")
    
    @staticmethod
    def from_yaml_file(file_path: Path) -> Union[ModelIR, List[ModelIR]]:
        """
        Read ModelIR from YAML file.
        
        Args:
            file_path: Input file path
            
        Returns:
            ModelIR or list of ModelIR objects
            
        Raises:
            ImportError: If PyYAML is not available
        """
        yaml_str = file_path.read_text(encoding='utf-8')
        models = IRSerializer.from_yaml(yaml_str)
        logger.info(f"Loaded IR from YAML file: {file_path}")
        return models
