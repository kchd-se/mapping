"""Adapter Registry — discovery and resolution of registered adapters.

Design:
- Adapters self-register via register_input() / register_output_source().
- The registry is a plain in-process singleton (no file I/O, no network).
  Future phases (catalog, API) will drive registration from configuration.
- Resolution is by format identifier string; the most recently registered
  adapter for a format wins (last-wins allows deployments to override
  built-ins without modifying core — AC-08, RL-11).
- The registry never imports format-specific code: it only holds references
  to adapter instances (RL-05).
"""

from __future__ import annotations

from typing import Dict, List, Optional

from packages.adapters.base import (
    AdapterNotFoundError,
    InputSchemaAdapter,
    OutputSchemaSource,
)


class AdapterRegistry:
    """Thread-unsafe, in-process registry of input and output adapters.

    Instantiate one registry per application context.  A module-level
    default registry (_DEFAULT_REGISTRY) is provided for convenience.
    """

    def __init__(self) -> None:
        # format_id -> list of adapters, in registration order
        self._input_adapters: Dict[str, List[InputSchemaAdapter]] = {}
        self._output_sources: Dict[str, List[OutputSchemaSource]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_input(self, adapter: InputSchemaAdapter) -> None:
        """Register an input adapter for all its declared formats."""
        for fmt in adapter.metadata.supported_formats:
            self._input_adapters.setdefault(fmt, []).append(adapter)

    def register_output_source(self, source: OutputSchemaSource) -> None:
        """Register an output schema source for all its declared formats."""
        for fmt in source.metadata.supported_formats:
            self._output_sources.setdefault(fmt, []).append(source)

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve_input(self, format_id: str) -> InputSchemaAdapter:
        """Return the best-match (last registered) input adapter for *format_id*.

        Args:
            format_id: Format identifier string (e.g. "json_schema").

        Returns:
            The most recently registered InputSchemaAdapter for the format.

        Raises:
            AdapterNotFoundError: If no adapter supports *format_id*.
        """
        candidates = self._input_adapters.get(format_id, [])
        if not candidates:
            raise AdapterNotFoundError(
                f"No input adapter registered for format {format_id!r}. "
                f"Registered formats: {self.list_input_formats()}"
            )
        return candidates[-1]  # last-wins

    def resolve_output_source(self, format_id: str) -> OutputSchemaSource:
        """Return the best-match output source for *format_id*.

        Raises:
            AdapterNotFoundError: If no source supports *format_id*.
        """
        candidates = self._output_sources.get(format_id, [])
        if not candidates:
            raise AdapterNotFoundError(
                f"No output source registered for format {format_id!r}. "
                f"Registered formats: {self.list_output_formats()}"
            )
        return candidates[-1]

    def get_all_input_adapters(self, format_id: str) -> List[InputSchemaAdapter]:
        """Return all registered input adapters for *format_id* (oldest first)."""
        return list(self._input_adapters.get(format_id, []))

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_input_formats(self) -> List[str]:
        """Return a sorted list of all registered input format identifiers."""
        return sorted(self._input_adapters.keys())

    def list_output_formats(self) -> List[str]:
        """Return a sorted list of all registered output format identifiers."""
        return sorted(self._output_sources.keys())

    def is_input_format_supported(self, format_id: str) -> bool:
        return bool(self._input_adapters.get(format_id))

    def is_output_format_supported(self, format_id: str) -> bool:
        return bool(self._output_sources.get(format_id))


# ---------------------------------------------------------------------------
# Module-level default registry
# ---------------------------------------------------------------------------

_DEFAULT_REGISTRY = AdapterRegistry()


def get_default_registry() -> AdapterRegistry:
    """Return the process-level default AdapterRegistry."""
    return _DEFAULT_REGISTRY
