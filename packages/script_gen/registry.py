"""Script generator registry.

Maps generator_id strings to ScriptGenerator instances.
The export router asks the registry for the default generator; tests and
future callers can request a specific generator by ID.

Adding a new generator
----------------------
1. Implement ``ScriptGenerator`` protocol in a new file under ``generators/``.
2. Import it here and pass an instance to ``register()``.
3. Nothing else changes.
"""

from __future__ import annotations

from typing import Dict

from packages.script_gen.generators.sql_insert_select import SqlInsertSelectGenerator
from packages.script_gen.interface import ScriptGenerator

_DEFAULT_GENERATOR_ID = "sql_insert_select_v1"

_registry: Dict[str, ScriptGenerator] = {}


def register(generator: ScriptGenerator) -> None:
    _registry[generator.generator_id] = generator


def get(generator_id: str) -> ScriptGenerator:
    gen = _registry.get(generator_id)
    if gen is None:
        raise KeyError(
            f"No script generator registered with id '{generator_id}'. "
            f"Available: {sorted(_registry)}"
        )
    return gen


def get_default() -> ScriptGenerator:
    return get(_DEFAULT_GENERATOR_ID)


def register_defaults() -> None:
    """Register all built-in generators.  Called once at app startup."""
    register(SqlInsertSelectGenerator())


# Register defaults on import so tests and the app both get them automatically.
register_defaults()
