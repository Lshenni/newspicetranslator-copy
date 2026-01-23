"""
Translator factory for creating format-specific translators.

This module provides a factory pattern implementation for creating the appropriate
translator based on source and target SPICE formats.
"""

from typing import Optional
from .base_translator import BaseTranslator, Format, InvalidFormatError
from .spectre_to_hspice_translator import SpectreToHSPICETranslator
from .hspice_to_spectre_translator import HSPICEToSpectreTranslator
from .ngspice_to_hspice_translator import NgspiceToHSPICETranslator
from .hspice_to_ngspice_translator import HSPICEToNgspiceTranslator
from .spectre_to_ngspice_translator import SpectreToNgspiceTranslator
import logging

logger = logging.getLogger(__name__)


class TranslatorFactory:
    """Factory for creating SPICE format translators."""

    # Registry of available translators
    _translators = {
        (Format.SPECTRE, Format.HSPICE): SpectreToHSPICETranslator,
        (Format.HSPICE, Format.SPECTRE): HSPICEToSpectreTranslator,
        (Format.NGSPICE, Format.HSPICE): NgspiceToHSPICETranslator,
        (Format.HSPICE, Format.NGSPICE): HSPICEToNgspiceTranslator,
        (Format.SPECTRE, Format.NGSPICE): SpectreToNgspiceTranslator,
    }

    @classmethod
    def create_translator(cls, source_format: Format, target_format: Format) -> BaseTranslator:
        """Create a translator for the specified source and target formats.

        Args:
            source_format: Source SPICE format
            target_format: Target SPICE format

        Returns:
            Configured translator instance

        Raises:
            InvalidFormatError: If the format pair is not supported
        """
        if source_format == target_format:
            raise InvalidFormatError("Source and target formats must be different")

        translator_key = (source_format, target_format)

        if translator_key not in cls._translators:
            available_pairs = [f"{src.value}->{tgt.value}" for src, tgt in cls._translators.keys()]
            raise InvalidFormatError(
                f"Translation from {source_format.value} to {target_format.value} is not supported. "
                f"Available pairs: {', '.join(available_pairs)}"
            )

        translator_class = cls._translators[translator_key]
        translator = translator_class()

        logger.info(f"Created translator: {source_format.value} -> {target_format.value}")
        return translator

    @classmethod
    def get_supported_translations(cls) -> list[tuple[Format, Format]]:
        """Get list of supported translation pairs.

        Returns:
            List of (source_format, target_format) tuples
        """
        return list(cls._translators.keys())

    @classmethod
    def is_supported(cls, source_format: Format, target_format: Format) -> bool:
        """Check if a translation pair is supported.

        Args:
            source_format: Source SPICE format
            target_format: Target SPICE format

        Returns:
            True if the translation pair is supported
        """
        return (source_format, target_format) in cls._translators

    @classmethod
    def get_available_targets(cls, source_format: Format) -> list[Format]:
        """Get available target formats for a given source format.

        Args:
            source_format: Source SPICE format

        Returns:
            List of supported target formats
        """
        return [target for src, target in cls._translators.keys() if src == source_format]

    @classmethod
    def get_available_sources(cls, target_format: Format) -> list[Format]:
        """Get available source formats for a given target format.

        Args:
            target_format: Target SPICE format

        Returns:
            List of supported source formats
        """
        return [source for source, tgt in cls._translators.keys() if tgt == target_format]


def create_translator(source_format: str, target_format: str) -> BaseTranslator:
    """Convenience function to create a translator from string format names.

    Args:
        source_format: Source format name ('spectre', 'hspice', 'ngspice')
        target_format: Target format name ('spectre', 'hspice', 'ngspice')

    Returns:
        Configured translator instance

    Raises:
        InvalidFormatError: If format names are invalid or pair is not supported
    """
    try:
        src_fmt = Format(source_format.lower())
        tgt_fmt = Format(target_format.lower())
    except ValueError as e:
        valid_formats = [fmt.value for fmt in Format]
        raise InvalidFormatError(
            f"Invalid format name. Valid formats: {', '.join(valid_formats)}"
        ) from e

    return TranslatorFactory.create_translator(src_fmt, tgt_fmt)


def list_supported_translations() -> None:
    """Print list of all supported translations."""
    translations = TranslatorFactory.get_supported_translations()

    print("Supported SPICE Format Translations:")
    print("=" * 40)

    for source, target in translations:
        print(f"  {source.value} -> {target.value}")

    print(f"\nTotal supported translation pairs: {len(translations)}")


def get_translation_info(source_format: Optional[str] = None) -> None:
    """Print detailed information about supported translations.

    Args:
        source_format: Optional source format to filter by
    """
    if source_format:
        try:
            src_fmt = Format(source_format.lower())
            targets = TranslatorFactory.get_available_targets(src_fmt)
            print(f"Available targets for {source_format}:")
            for target in targets:
                print(f"  - {target.value}")
        except ValueError:
            print(f"Unknown format: {source_format}")
    else:
        print("SPICE Translation Matrix:")
        print("=" * 30)
        all_formats = list(Format)

        # Print header
        print("From/To   ", end="")
        for fmt in all_formats:
            print("8", end="")
        print()

        # Print separator
        print("-" * (10 + len(all_formats) * 8))

        # Print matrix
        for src in all_formats:
            print("8", end="")
            for tgt in all_formats:
                if TranslatorFactory.is_supported(src, tgt):
                    print("   ✓    ", end="")
                elif src == tgt:
                    print("   ---  ", end="")
                else:
                    print("   ---  ", end="")
            print()

        print("\n✓ = Supported translation")
        print("--- = Not supported or same format")
