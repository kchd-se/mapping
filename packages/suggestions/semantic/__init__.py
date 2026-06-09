"""Semantic similarity sub-package for the suggestion engine.

Public surface:
    SemanticDescriptor          — data object describing a field for semantic matching
    SemanticSimilarityProvider  — protocol all providers must satisfy
    SemanticScore               — result object returned by a provider
    LexicalSemanticProvider     — default deterministic v1 provider
"""

from packages.suggestions.semantic.interface import (
    SemanticDescriptor,
    SemanticScore,
    SemanticSimilarityProvider,
)
from packages.suggestions.semantic.default_provider import LexicalSemanticProvider

__all__ = [
    "SemanticDescriptor",
    "SemanticScore",
    "SemanticSimilarityProvider",
    "LexicalSemanticProvider",
]
