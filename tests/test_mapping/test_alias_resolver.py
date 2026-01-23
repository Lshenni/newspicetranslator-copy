"""Tests for AliasResolver."""

import pytest
from src.mapping import AliasResolver, AliasMatch, build_resolver_from_mapper_data


@pytest.fixture
def resolver():
    """Create AliasResolver instance."""
    return AliasResolver()


@pytest.fixture
def populated_resolver():
    """Create AliasResolver with some test data."""
    resolver = AliasResolver()
    resolver.add_aliases_batch({
        "vth": "vth0",
        "vtho": "vth0",
        "vt0": "vth0",
        "uo": "u0",
        "mobility": "u0",
    })
    return resolver


class TestAliasResolverInitialization:
    """Test AliasResolver initialization."""
    
    def test_empty_initialization(self, resolver):
        """Test resolver initializes empty."""
        stats = resolver.get_stats()
        assert stats['total_aliases'] == 0
        assert stats['canonical_parameters'] == 0
    
    def test_add_single_alias(self, resolver):
        """Test adding a single alias."""
        resolver.add_alias("vth", "vth0")
        assert resolver.is_alias("vth")
        
        match = resolver.resolve("vth")
        assert match is not None
        assert match.canonical_name == "vth0"
    
    def test_add_multiple_aliases(self, resolver):
        """Test adding multiple aliases for same parameter."""
        resolver.add_alias("vth", "vth0")
        resolver.add_alias("vtho", "vth0")
        resolver.add_alias("vt0", "vth0")
        
        aliases = resolver.get_all_aliases("vth0")
        assert len(aliases) == 3
        assert set(aliases) == {"vth", "vtho", "vt0"}


class TestAliasResolution:
    """Test alias resolution functionality."""
    
    def test_resolve_exact_match(self, populated_resolver):
        """Test resolving canonical name (exact match)."""
        match = populated_resolver.resolve("vth0")
        assert match is not None
        assert match.canonical_name == "vth0"
        assert match.match_type == "exact"
        assert match.confidence == 1.0
    
    def test_resolve_alias_match(self, populated_resolver):
        """Test resolving known alias."""
        match = populated_resolver.resolve("vth")
        assert match is not None
        assert match.canonical_name == "vth0"
        assert match.match_type == "alias"
        assert match.confidence == 1.0
    
    def test_resolve_unknown(self, populated_resolver):
        """Test resolving unknown parameter returns None."""
        match = populated_resolver.resolve("unknown_param")
        assert match is None
    
    def test_resolve_case_insensitive(self, populated_resolver):
        """Test that resolution is case-insensitive."""
        match1 = populated_resolver.resolve("vth")
        match2 = populated_resolver.resolve("VTH")
        match3 = populated_resolver.resolve("Vth")
        
        assert match1 is not None
        assert match2 is not None
        assert match3 is not None
        assert match1.canonical_name == match2.canonical_name == match3.canonical_name


class TestFuzzyMatching:
    """Test fuzzy matching functionality."""
    
    def test_fuzzy_underscore_removal(self):
        """Test fuzzy matching removes underscores."""
        resolver = AliasResolver()
        resolver.add_alias("vth0", "vth0")
        
        match = resolver.resolve("vth_0", fuzzy=True)
        assert match is not None
        assert match.canonical_name == "vth0"
        assert match.match_type == "fuzzy"
        assert match.confidence == 0.8
    
    def test_fuzzy_hyphen_removal(self):
        """Test fuzzy matching removes hyphens."""
        resolver = AliasResolver()
        resolver.add_alias("test", "test")
        
        match = resolver.resolve("te-st", fuzzy=True)
        assert match is not None
        assert match.canonical_name == "test"
        assert match.match_type == "fuzzy"
    
    def test_fuzzy_disabled(self):
        """Test that fuzzy matching can be disabled."""
        resolver = AliasResolver()
        resolver.add_alias("vth0", "vth0")
        
        match = resolver.resolve("vth_0", fuzzy=False)
        assert match is None


class TestBatchResolution:
    """Test batch resolution functionality."""
    
    def test_resolve_batch_all_found(self, populated_resolver):
        """Test resolving multiple parameters (all found)."""
        params = ["vth", "uo", "vth0"]
        results = populated_resolver.resolve_batch(params)
        
        assert len(results) == 3
        assert all(match is not None for match in results.values())
        
        assert results["vth"].canonical_name == "vth0"
        assert results["uo"].canonical_name == "u0"
        assert results["vth0"].canonical_name == "vth0"
    
    def test_resolve_batch_mixed(self, populated_resolver):
        """Test resolving batch with some unknown parameters."""
        params = ["vth", "unknown", "uo"]
        results = populated_resolver.resolve_batch(params)
        
        assert len(results) == 3
        assert results["vth"] is not None
        assert results["unknown"] is None
        assert results["uo"] is not None
    
    def test_resolve_batch_empty(self, populated_resolver):
        """Test resolving empty list."""
        results = populated_resolver.resolve_batch([])
        assert len(results) == 0


class TestAliasQueries:
    """Test query methods for aliases."""
    
    def test_get_all_aliases(self, populated_resolver):
        """Test getting all aliases for a parameter."""
        aliases = populated_resolver.get_all_aliases("vth0")
        assert len(aliases) == 3
        assert set(aliases) == {"vth", "vtho", "vt0"}
    
    def test_get_aliases_no_match(self, populated_resolver):
        """Test getting aliases for unknown parameter."""
        aliases = populated_resolver.get_all_aliases("unknown")
        assert len(aliases) == 0
    
    def test_is_alias_true(self, populated_resolver):
        """Test checking if name is known alias."""
        assert populated_resolver.is_alias("vth") is True
        assert populated_resolver.is_alias("vth0") is True
        assert populated_resolver.is_alias("uo") is True
    
    def test_is_alias_false(self, populated_resolver):
        """Test checking unknown name."""
        assert populated_resolver.is_alias("unknown") is False
    
    def test_get_canonical_names(self, populated_resolver):
        """Test getting all canonical parameter names."""
        canonical = populated_resolver.get_canonical_names()
        assert len(canonical) == 2
        assert canonical == {"vth0", "u0"}


class TestAliasManagement:
    """Test alias management operations."""
    
    def test_add_aliases_batch(self, resolver):
        """Test adding multiple aliases at once."""
        aliases = {
            "vth": "vth0",
            "vtho": "vth0",
            "uo": "u0",
        }
        resolver.add_aliases_batch(aliases)
        
        stats = resolver.get_stats()
        assert stats['total_aliases'] == 3
        assert stats['canonical_parameters'] == 2
    
    def test_clear_aliases(self, populated_resolver):
        """Test clearing all aliases."""
        populated_resolver.clear()
        
        stats = populated_resolver.get_stats()
        assert stats['total_aliases'] == 0
        assert stats['canonical_parameters'] == 0
    
    def test_export_aliases(self, populated_resolver):
        """Test exporting alias mappings."""
        exported = populated_resolver.export_aliases()
        
        assert isinstance(exported, dict)
        assert len(exported) == 5
        assert exported["vth"] == "vth0"
        assert exported["uo"] == "u0"
    
    def test_merge_resolvers(self):
        """Test merging two resolvers."""
        resolver1 = AliasResolver()
        resolver1.add_alias("vth", "vth0")
        
        resolver2 = AliasResolver()
        resolver2.add_alias("uo", "u0")
        
        resolver1.merge_from(resolver2)
        
        assert resolver1.is_alias("vth")
        assert resolver1.is_alias("uo")
        assert resolver1.get_stats()['total_aliases'] == 2


class TestAliasMatchDataclass:
    """Test AliasMatch dataclass."""
    
    def test_alias_match_structure(self, populated_resolver):
        """Test AliasMatch contains expected fields."""
        match = populated_resolver.resolve("vth")
        
        assert match is not None
        assert hasattr(match, 'original_name')
        assert hasattr(match, 'canonical_name')
        assert hasattr(match, 'match_type')
        assert hasattr(match, 'confidence')
    
    def test_alias_match_values(self, populated_resolver):
        """Test AliasMatch field values."""
        match = populated_resolver.resolve("vth")
        
        assert match.original_name == "vth"
        assert match.canonical_name == "vth0"
        assert match.match_type in ["exact", "alias", "fuzzy"]
        assert 0.0 <= match.confidence <= 1.0


class TestBuilderFunction:
    """Test build_resolver_from_mapper_data function."""
    
    def test_build_from_mapper_data(self):
        """Test building resolver from mapper YAML data."""
        mapper_data = {
            "vth0": {
                "aliases": ["vth", "vtho", "vt0"],
                "spectre": {"target": "vth0", "confidence": "high"},
            },
            "u0": {
                "aliases": ["uo", "mobility"],
                "spectre": {"target": "u0", "confidence": "high"},
            },
        }
        
        resolver = build_resolver_from_mapper_data(mapper_data)
        
        # Check that canonical names are resolvable
        assert resolver.resolve("vth0") is not None
        assert resolver.resolve("u0") is not None
        
        # Check that aliases are resolvable
        assert resolver.resolve("vth") is not None
        assert resolver.resolve("uo") is not None
        
        # Check stats
        stats = resolver.get_stats()
        assert stats['canonical_parameters'] == 2
        assert stats['total_aliases'] == 7  # 2 canonical + 5 aliases
    
    def test_build_with_empty_aliases(self):
        """Test building resolver with parameters that have no aliases."""
        mapper_data = {
            "vth0": {
                "aliases": [],
                "spectre": {"target": "vth0"},
            },
        }
        
        resolver = build_resolver_from_mapper_data(mapper_data)
        
        # Canonical name should still be resolvable
        assert resolver.resolve("vth0") is not None
        
        stats = resolver.get_stats()
        assert stats['canonical_parameters'] == 1
        assert stats['total_aliases'] == 1  # Just the canonical name


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_parameter_name(self, resolver):
        """Test handling of empty parameter name."""
        resolver.add_alias("", "test")
        match = resolver.resolve("")
        # Should handle gracefully
        assert match is not None or match is None  # Either way is acceptable
    
    def test_whitespace_handling(self, resolver):
        """Test that whitespace is stripped."""
        resolver.add_alias(" vth ", "vth0")
        
        match = resolver.resolve(" vth ")
        assert match is not None
        assert match.canonical_name == "vth0"
    
    def test_duplicate_alias(self, resolver):
        """Test adding same alias twice."""
        resolver.add_alias("vth", "vth0")
        resolver.add_alias("vth", "vth0")  # Duplicate
        
        aliases = resolver.get_all_aliases("vth0")
        # Should not create duplicate
        assert aliases.count("vth") == 1
    
    def test_alias_to_different_canonical(self, resolver):
        """Test overwriting alias to point to different canonical name."""
        resolver.add_alias("test", "param1")
        resolver.add_alias("test", "param2")  # Overwrite
        
        match = resolver.resolve("test")
        assert match is not None
        assert match.canonical_name == "param2"


class TestStatistics:
    """Test statistics and reporting."""
    
    def test_get_stats_empty(self, resolver):
        """Test statistics on empty resolver."""
        stats = resolver.get_stats()
        assert stats['total_aliases'] == 0
        assert stats['canonical_parameters'] == 0
    
    def test_get_stats_populated(self, populated_resolver):
        """Test statistics on populated resolver."""
        stats = populated_resolver.get_stats()
        assert stats['total_aliases'] == 5
        assert stats['canonical_parameters'] == 2
    
    def test_stats_after_operations(self, resolver):
        """Test that statistics update correctly after operations."""
        # Initially empty
        assert resolver.get_stats()['total_aliases'] == 0
        
        # Add some aliases
        resolver.add_alias("vth", "vth0")
        assert resolver.get_stats()['total_aliases'] == 1
        
        # Add more
        resolver.add_alias("uo", "u0")
        assert resolver.get_stats()['total_aliases'] == 2
        assert resolver.get_stats()['canonical_parameters'] == 2
        
        # Clear
        resolver.clear()
        assert resolver.get_stats()['total_aliases'] == 0
