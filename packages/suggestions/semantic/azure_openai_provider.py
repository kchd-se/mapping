"""Azure OpenAI Embedding Provider — semantic similarity via embeddings.

Uses the Azure OpenAI Embeddings REST API to generate embedding vectors and
computes cosine similarity between source and target field descriptors.

Config (environment variables)
-------------------------------
AZURE_OPENAI_ENDPOINT
    Base URL for the Azure OpenAI resource, e.g.
    ``https://<resource-name>.openai.azure.com``
AZURE_OPENAI_API_KEY
    API key for the resource.
AZURE_OPENAI_EMBEDDING_DEPLOYMENT
    Deployment name of the embedding model, e.g. ``text-embedding-3-small``.
AZURE_OPENAI_API_VERSION
    Azure OpenAI API version (default: ``2024-02-01``).

On-prem / offline fallback
---------------------------
If any required env var is absent, OR if an API call fails at runtime, the
provider falls back to ``LexicalSemanticProvider`` (deterministic, no network).
This satisfies the on-prem deployment and offline-fallback requirements
(AC-07) without code forks (RL-07).

Caching
-------
Embedding vectors are cached in-memory keyed by ``semantic_text``.  Each
unique text value is only sent to the API once per process lifetime, keeping
suggestion latency low for large schemas.
"""

from __future__ import annotations

import math
import os
from typing import List, Optional

import httpx

from packages.suggestions.semantic.default_provider import LexicalSemanticProvider
from packages.suggestions.semantic.interface import (
    SemanticDescriptor,
    SemanticScore,
)

# ---------------------------------------------------------------------------
# Env-var names (constants to avoid magic strings)
# ---------------------------------------------------------------------------

_ENV_ENDPOINT = "AZURE_OPENAI_ENDPOINT"
_ENV_API_KEY = "AZURE_OPENAI_API_KEY"
_ENV_DEPLOYMENT = "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
_ENV_API_VERSION = "AZURE_OPENAI_API_VERSION"
_DEFAULT_API_VERSION = "2024-02-01"

# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(v: List[float]) -> float:
    return math.sqrt(_dot(v, v))


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity in [0, 1]. Returns 0.0 for zero-norm vectors."""
    na, nb = _norm(a), _norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    raw = _dot(a, b) / (na * nb)
    # Clamp to [−1, 1] to guard against floating-point drift, then shift to [0, 1].
    clamped = max(-1.0, min(1.0, raw))
    return (clamped + 1.0) / 2.0


# ---------------------------------------------------------------------------
# Azure OpenAI Embedding Provider
# ---------------------------------------------------------------------------


class AzureOpenAIEmbeddingProvider:
    """SemanticSimilarityProvider backed by Azure OpenAI embeddings.

    This provider intentionally makes network calls, which deviates from the
    "side-effect free" note in the protocol docstring.  That note applies to
    purely local providers; this class extends the protocol for
    network-backed semantics while satisfying the same ``compute`` signature.

    Falls back to ``LexicalSemanticProvider`` when the API is unreachable or
    returns an error, so suggestions always succeed even offline.
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str = _DEFAULT_API_VERSION,
        timeout: float = 10.0,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._api_key = api_key
        self._deployment = deployment
        self._api_version = api_version
        self._timeout = timeout
        self._cache: dict[str, List[float]] = {}
        self._fallback = LexicalSemanticProvider()

    # ------------------------------------------------------------------
    # Public API (SemanticSimilarityProvider protocol)
    # ------------------------------------------------------------------

    def compute(
        self,
        source: SemanticDescriptor,
        target: SemanticDescriptor,
    ) -> SemanticScore:
        try:
            src_vec = self._embed(source.semantic_text)
            tgt_vec = self._embed(target.semantic_text)
            sim = round(cosine_similarity(src_vec, tgt_vec), 4)
            explanation = (
                f"Azure OpenAI embedding cosine similarity={sim:.4f} "
                f"('{source.field_name}' vs '{target.field_name}')"
            )
            return SemanticScore(similarity=sim, explanation=explanation)
        except Exception as exc:  # noqa: BLE001
            # Degrade gracefully — log and fall back to lexical.
            fallback_score = self._fallback.compute(source, target)
            explanation = (
                f"Azure OpenAI unavailable ({type(exc).__name__}); "
                f"lexical fallback: {fallback_score.explanation}"
            )
            return SemanticScore(
                similarity=fallback_score.similarity,
                explanation=explanation,
            )

    # ------------------------------------------------------------------
    # Embedding with caching
    # ------------------------------------------------------------------

    def _embed(self, text: str) -> List[float]:
        """Return the embedding vector for *text*, using cache if available."""
        if text in self._cache:
            return self._cache[text]
        vector = self._fetch_embedding(text)
        self._cache[text] = vector
        return vector

    def _fetch_embedding(self, text: str) -> List[float]:
        """Call the Azure OpenAI Embeddings API and return the vector."""
        url = (
            f"{self._endpoint}/openai/deployments/{self._deployment}"
            f"/embeddings?api-version={self._api_version}"
        )
        payload = {"input": text}
        headers = {"api-key": self._api_key, "Content-Type": "application/json"}

        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(url, json=payload, headers=headers)

        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    # ------------------------------------------------------------------
    # Cache inspection (useful for tests and monitoring)
    # ------------------------------------------------------------------

    @property
    def cache_size(self) -> int:
        """Number of unique texts currently cached."""
        return len(self._cache)

    def clear_cache(self) -> None:
        """Evict all cached embeddings (e.g. after schema catalog changes)."""
        self._cache.clear()


# ---------------------------------------------------------------------------
# Factory function — reads env vars and returns the appropriate provider
# ---------------------------------------------------------------------------


def build_semantic_provider(
    semantic_weight: float = 0.25,
) -> object:
    """Return ``AzureOpenAIEmbeddingProvider`` if configured, else ``LexicalSemanticProvider``.

    Reads ``AZURE_OPENAI_ENDPOINT``, ``AZURE_OPENAI_API_KEY``, and
    ``AZURE_OPENAI_EMBEDDING_DEPLOYMENT`` from the environment.  If any are
    missing the lexical provider is returned so the system works offline /
    on-prem without any additional configuration.

    The returned object satisfies the ``SemanticSimilarityProvider`` protocol
    in either case.

    Args:
        semantic_weight: Not used by this function but documented here for
            discoverability — pass it to ``SuggestionEngine(semantic_weight=...)``.
    """
    endpoint: Optional[str] = os.getenv(_ENV_ENDPOINT)
    api_key: Optional[str] = os.getenv(_ENV_API_KEY)
    deployment: Optional[str] = os.getenv(_ENV_DEPLOYMENT)
    api_version: str = os.getenv(_ENV_API_VERSION, _DEFAULT_API_VERSION)

    if endpoint and api_key and deployment:
        return AzureOpenAIEmbeddingProvider(
            endpoint=endpoint,
            api_key=api_key,
            deployment=deployment,
            api_version=api_version,
        )

    return LexicalSemanticProvider()
