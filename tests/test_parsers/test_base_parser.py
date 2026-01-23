"""
Unit tests for base parser.

Tests the abstract base parser functionality.

Compliance: CONSTRAINTS.md - pytest only
"""

import pytest
from pathlib import Path
from src.parsers.base_parser import BaseParser
from src.ir.model_ir import ModelIR, DeviceType


class MockParser(BaseParser):
    """Mock parser for testing base functionality."""
    
    def get_format_name(self) -> str:
        return "mock"
    
    def parse_to_ir(self, follow_includes: bool = False):
        """Simple implementation for testing."""
        return [
            ModelIR(
                name="test_model",
                model_type="bsim4",
                device_type=DeviceType.NMOS
            )
        ]


class TestBaseParser:
    """Test BaseParser functionality."""
    
    def test_parser_initialization(self, tmp_path):
        """Test parser initialization with valid file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        parser = MockParser(test_file)
        assert parser.file_path == test_file
        assert parser.content == "test content"
        assert len(parser.included_files) == 0
    
    def test_parser_file_not_found(self):
        """Test parser raises error for missing file."""
        with pytest.raises(FileNotFoundError):
            MockParser(Path("/nonexistent/file.txt"))
    
    def test_load_file_utf8(self, tmp_path):
        """Test loading UTF-8 file."""
        test_file = tmp_path / "utf8.txt"
        test_file.write_text("UTF-8 content: α β γ", encoding='utf-8')
        
        parser = MockParser(test_file)
        assert "α β γ" in parser.content
    
    def test_load_file_fallback_latin1(self, tmp_path):
        """Test fallback to latin-1 encoding."""
        test_file = tmp_path / "latin1.txt"
        # Write with latin-1 encoding
        test_file.write_bytes(b"Latin-1: \xe9 \xe0")
        
        parser = MockParser(test_file)
        # Should load without error (fallback to latin-1)
        assert parser.content is not None
    
    def test_get_format_name(self, tmp_path):
        """Test format name retrieval."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        parser = MockParser(test_file)
        assert parser.get_format_name() == "mock"
    
    def test_parse_to_ir_basic(self, tmp_path):
        """Test basic parse_to_ir call."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        parser = MockParser(test_file)
        models = parser.parse_to_ir()
        
        assert isinstance(models, list)
        assert len(models) == 1
        assert models[0].name == "test_model"
    
    def test_get_included_files(self, tmp_path):
        """Test getting included files."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        parser = MockParser(test_file)
        included = parser.get_included_files()
        
        assert isinstance(included, set)
        assert len(included) == 0
    
    def test_resolve_include_path_relative(self, tmp_path):
        """Test resolving relative include path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        include_file = tmp_path / "included.txt"
        include_file.write_text("included")
        
        parser = MockParser(test_file)
        resolved = parser._resolve_include_path("included.txt")
        
        assert resolved is not None
        assert resolved.name == "included.txt"
    
    def test_resolve_include_path_not_found(self, tmp_path):
        """Test resolving non-existent include path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        parser = MockParser(test_file)
        resolved = parser._resolve_include_path("nonexistent.txt")
        
        assert resolved is None
    
    def test_validate_content_valid(self, tmp_path):
        """Test content validation with valid content."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("valid content")
        
        parser = MockParser(test_file)
        assert parser.validate_content() is True
    
    def test_validate_content_empty(self, tmp_path):
        """Test content validation with empty content."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")
        
        parser = MockParser(test_file)
        assert parser.validate_content() is False
    
    def test_parser_repr(self, tmp_path):
        """Test parser string representation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        parser = MockParser(test_file)
        repr_str = repr(parser)
        
        assert "MockParser" in repr_str
        assert "test.txt" in repr_str
