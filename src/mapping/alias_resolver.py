"""
Alias Resolver for SPICE parameter names.

This module resolves parameter name aliases and variations to canonical
names, supporting fuzzy matching and common naming conventions across
different SPICE formats.

Compliance: CONSTRAINTS.md
- Complete implementation (no TODOs)
- Full type annotations
- Google-style docstrings
- <1000 lines per file
"""

from typing import Dict, List, Optional, Set
import logging
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class AliasMatch:
    """Result of alias resolution."""
    original_name: str
    canonical_name: str
    match_type: str  # exact, alias, fuzzy
    confidence: float  # 0.0 to 1.0


class AliasResolver:
    """
    Resolves parameter name aliases to canonical names.
    
    Handles common variations in parameter naming:
    - Case insensitivity (VTH0 -> vth0)
    - Common aliases (vth -> vth0, uo -> u0)
    - Underscores vs no underscores (vth_0 -> vth0)
    - Number variations (tox vs toxe)
    
    Attributes:
        _alias_map: Mapping from alias to canonical name.
        _fuzzy_patterns: Common patterns for fuzzy matching.
    
    Example:
        >>> resolver = AliasResolver()
        >>> resolver.add_alias("vth", "vth0")
        >>> resolver.add_alias("vtho", "vth0")
        >>> match = resolver.resolve("VTH")
        >>> print(match.canonical_name)
        vth0
    """
    
    def __init__(self) -> None:
        """Initialize alias resolver."""
        self._alias_map: Dict[str, str] = {}
        self._fuzzy_patterns: List[tuple] = [
            # Pattern replacements for fuzzy matching
            ('_', ''),  # Remove underscores
            ('-', ''),  # Remove hyphens
        ]
        logger.debug("Initialized AliasResolver")
    
    def add_alias(self, alias: str, canonical_name: str) -> None:
        """
        Add an alias mapping.
        
        Args:
            alias: Alias name (case-insensitive).
            canonical_name: Canonical parameter name.
        
        Example:
            >>> resolver = AliasResolver()
            >>> resolver.add_alias("vth", "vth0")
            >>> resolver.add_alias("vtho", "vth0")
        """
        normalized_alias = alias.lower().strip()
        self._alias_map[normalized_alias] = canonical_name
        logger.debug(f"Added alias: {normalized_alias} -> {canonical_name}")
    
    def add_aliases_batch(self, aliases: Dict[str, str]) -> None:
        """
        Add multiple alias mappings at once.
        
        Args:
            aliases: Dictionary mapping alias names to canonical names.
        
        Example:
            >>> resolver = AliasResolver()
            >>> resolver.add_aliases_batch({
            ...     "vth": "vth0",
            ...     "vtho": "vth0",
            ...     "uo": "u0"
            ... })
        """
        for alias, canonical_name in aliases.items():
            self.add_alias(alias, canonical_name)
        
        logger.info(f"Added {len(aliases)} alias mappings")
    
    def resolve(self, param_name: str, fuzzy: bool = True) -> Optional[AliasMatch]:
        """
        Resolve parameter name to canonical form.
        
        Args:
            param_name: Parameter name to resolve.
            fuzzy: Enable fuzzy matching (default: True).
        
        Returns:
            AliasMatch with canonical name and match details,
            or None if no match found.
        
        Example:
            >>> resolver = AliasResolver()
            >>> resolver.add_alias("vth", "vth0")
            >>> match = resolver.resolve("VTH")
            >>> print(f"{match.canonical_name} ({match.match_type})")
            vth0 (alias)
        """
        normalized = param_name.lower().strip()
        
        # Exact match (canonical name)
        if normalized in self._alias_map.values():
            return AliasMatch(
                original_name=param_name,
                canonical_name=normalized,
                match_type="exact",
                confidence=1.0
            )
        
        # Alias match
        if normalized in self._alias_map:
            return AliasMatch(
                original_name=param_name,
                canonical_name=self._alias_map[normalized],
                match_type="alias",
                confidence=1.0
            )
        
        # Fuzzy matching
        if fuzzy:
            fuzzy_match = self._fuzzy_match(normalized)
            if fuzzy_match is not None:
                return fuzzy_match
        
        logger.debug(f"No match found for parameter '{param_name}'")
        return None
    
    def _fuzzy_match(self, param_name: str) -> Optional[AliasMatch]:
        """
        Attempt fuzzy matching using common patterns.
        
        Args:
            param_name: Normalized parameter name.
        
        Returns:
            AliasMatch if fuzzy match found, None otherwise.
        """
        # Apply fuzzy transformations
        transformed = param_name
        for pattern, replacement in self._fuzzy_patterns:
            transformed = transformed.replace(pattern, replacement)
        
        # Check if transformed version matches
        if transformed in self._alias_map:
            return AliasMatch(
                original_name=param_name,
                canonical_name=self._alias_map[transformed],
                match_type="fuzzy",
                confidence=0.8
            )
        
        if transformed in self._alias_map.values():
            return AliasMatch(
                original_name=param_name,
                canonical_name=transformed,
                match_type="fuzzy",
                confidence=0.8
            )
        
        return None
    
    def resolve_batch(
        self, 
        param_names: List[str], 
        fuzzy: bool = True
    ) -> Dict[str, Optional[AliasMatch]]:
        """
        Resolve multiple parameter names.
        
        Args:
            param_names: List of parameter names to resolve.
            fuzzy: Enable fuzzy matching (default: True).
        
        Returns:
            Dictionary mapping original names to AliasMatch results.
        
        Example:
            >>> resolver = AliasResolver()
            >>> resolver.add_aliases_batch({"vth": "vth0", "uo": "u0"})
            >>> results = resolver.resolve_batch(["VTH", "UO", "unknown"])
            >>> for name, match in results.items():
            ...     if match:
            ...         print(f"{name} -> {match.canonical_name}")
            VTH -> vth0
            UO -> u0
        """
        results = {}
        for param_name in param_names:
            results[param_name] = self.resolve(param_name, fuzzy=fuzzy)
        
        matched = sum(1 for match in results.values() if match is not None)
        logger.info(f"Resolved {matched}/{len(param_names)} parameters")
        
        return results
    
    def get_all_aliases(self, canonical_name: str) -> List[str]:
        """
        Get all known aliases for a canonical parameter name.
        
        Args:
            canonical_name: Canonical parameter name.
        
        Returns:
            List of all known aliases for this parameter.
        
        Example:
            >>> resolver = AliasResolver()
            >>> resolver.add_aliases_batch({"vth": "vth0", "vtho": "vth0"})
            >>> aliases = resolver.get_all_aliases("vth0")
            >>> print(sorted(aliases))
            ['vth', 'vtho']
        """
        canonical_lower = canonical_name.lower()
        aliases = [
            alias for alias, canonical in self._alias_map.items()
            if canonical == canonical_lower
        ]
        return aliases
    
    def is_alias(self, param_name: str) -> bool:
        """
        Check if a parameter name is a known alias.
        
        Args:
            param_name: Parameter name to check.
        
        Returns:
            True if parameter is a known alias or canonical name.
        
        Example:
            >>> resolver = AliasResolver()
            >>> resolver.add_alias("vth", "vth0")
            >>> resolver.is_alias("vth")
            True
            >>> resolver.is_alias("vth0")
            True
            >>> resolver.is_alias("unknown")
            False
        """
        normalized = param_name.lower().strip()
        return (normalized in self._alias_map or 
                normalized in self._alias_map.values())
    
    def get_canonical_names(self) -> Set[str]:
        """
        Get all canonical parameter names.
        
        Returns:
            Set of canonical parameter names.
        
        Example:
            >>> resolver = AliasResolver()
            >>> resolver.add_aliases_batch({"vth": "vth0", "uo": "u0"})
            >>> canonical = resolver.get_canonical_names()
            >>> print(sorted(canonical))
            ['u0', 'vth0']
        """
        return set(self._alias_map.values())
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about loaded aliases.
        
        Returns:
            Dictionary with alias counts.
        
        Example:
            >>> resolver = AliasResolver()
            >>> resolver.add_aliases_batch({"vth": "vth0", "vtho": "vth0", "uo": "u0"})
            >>> stats = resolver.get_stats()
            >>> print(stats)
            {'total_aliases': 3, 'canonical_parameters': 2}
        """
        return {
            'total_aliases': len(self._alias_map),
            'canonical_parameters': len(set(self._alias_map.values()))
        }
    
    def export_aliases(self) -> Dict[str, str]:
        """
        Export all alias mappings.
        
        Returns:
            Dictionary of all alias to canonical name mappings.
        
        Example:
            >>> resolver = AliasResolver()
            >>> resolver.add_aliases_batch({"vth": "vth0", "uo": "u0"})
            >>> aliases = resolver.export_aliases()
            >>> print(aliases)
            {'vth': 'vth0', 'uo': 'u0'}
        """
        return self._alias_map.copy()
    
    def clear(self) -> None:
        """
        Clear all alias mappings.
        
        Example:
            >>> resolver = AliasResolver()
            >>> resolver.add_alias("vth", "vth0")
            >>> resolver.clear()
            >>> resolver.is_alias("vth")
            False
        """
        self._alias_map.clear()
        logger.info("Cleared all alias mappings")
    
    def merge_from(self, other: 'AliasResolver') -> None:
        """
        Merge aliases from another resolver.
        
        Args:
            other: Another AliasResolver instance to merge from.
        
        Example:
            >>> resolver1 = AliasResolver()
            >>> resolver1.add_alias("vth", "vth0")
            >>> resolver2 = AliasResolver()
            >>> resolver2.add_alias("uo", "u0")
            >>> resolver1.merge_from(resolver2)
            >>> resolver1.is_alias("uo")
            True
        """
        before_count = len(self._alias_map)
        self._alias_map.update(other._alias_map)
        after_count = len(self._alias_map)
        
        added = after_count - before_count
        logger.info(f"Merged {added} new aliases")


def build_resolver_from_mapper_data(
    mapper_data: Dict[str, Dict]
) -> AliasResolver:
    """
    Build AliasResolver from parameter mapper data.
    
    Args:
        mapper_data: Dictionary of parameter mapping data from YAML.
    
    Returns:
        Configured AliasResolver with all aliases loaded.
    
    Example:
        >>> data = {
        ...     "vth0": {"aliases": ["vth", "vtho"]},
        ...     "u0": {"aliases": ["uo", "mobility"]}
        ... }
        >>> resolver = build_resolver_from_mapper_data(data)
        >>> resolver.is_alias("vth")
        True
    """
    resolver = AliasResolver()
    
    for canonical_name, param_data in mapper_data.items():
        # Add canonical name to itself
        resolver.add_alias(canonical_name, canonical_name)
        
        # Add all aliases
        if isinstance(param_data, dict) and 'aliases' in param_data:
            for alias in param_data['aliases']:
                resolver.add_alias(alias, canonical_name)
    
    stats = resolver.get_stats()
    logger.info(
        f"Built resolver with {stats['total_aliases']} aliases "
        f"for {stats['canonical_parameters']} parameters"
    )
    
    return resolver
