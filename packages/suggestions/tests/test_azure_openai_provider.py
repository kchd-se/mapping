"""Unit tests for the Azure OpenAI Embedding Provider.

Covers:
- cosine_similarity: identical vectors → 1.0
- cosine_similarity: orthogonal vectors → 0.5 (shifted from [-1,1] to [0,1])
- cosine_similarity: zero vector → 0.0
- AzureOpenAIEmbeddingProvider: satisfies SemanticSimilarityProvider protocol
- AzureOpenAIEmbeddingProvider: caches embeddings (API called once per unique text)
- AzureOpenAIEmbeddingProvider: returns SemanticScore with valid similarity + explanation
- AzureOpenAIEmbeddingProvider: falls back to Lexical when API raises an error
- AzureOpenAIEmbeddingProvider: fallback explanation mentions the error type
- AzureOpenAIEmbeddingProvider: clear_cache resets the cache
- AzureOpenAIEmbeddingProvider: score similarity in [0, 1]
- build_semantic_provider: returns LexicalSemanticProvider when env vars are absent
- build_semantic_provider: returns AzureOpenAIEmbeddingProvider when env vars are set
"""

from __future__ import annotations

import os
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from packages.suggestions.semantic.azure_openai_provider import (
    AzureOpenAIEmbeddingProvider,
    build_semantic_provider,
    cosine_similarity,
)
from packages.suggestions.semantic.default_provider import LexicalSemanticProvider
from packages.suggestions.semantic.interface import (
    SemanticDescriptor,
    SemanticSimilarityProvider,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENDPOINT = "https://myresource.openai.azure.com"
_API_KEY = "test-api-key-abc123"
_DEPLOYMENT = "text-embedding-3-small"


def _make_provider(
    endpoint: str = _ENDPOINT,
    api_key: str = _API_KEY,
    deployment: str = _DEPLOYMENT,
) -> AzureOpenAIEmbeddingProvider:
    return AzureOpenAIEmbeddingProvider(
        endpoint=endpoint,
        api_key=api_key,
        deployment=deployment,
    )


def _desc(table: str, field: str, description: str | None = None) -> SemanticDescriptor:
    return SemanticDescriptor(table_name=table, field_name=field, description=description)


def _mock_embedding_response(vector: List[float]) -> MagicMock:
    """Return a mock httpx.Response with the given embedding vector."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"data": [{"embedding": vector}]}
    return mock_response


# ---------------------------------------------------------------------------
# cosine_similarity
# ---------------------------------------------------------------------------


def test_cosine_identical_vectors() -> None:
    v = [1.0, 0.0, 0.0]
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_opposite_vectors() -> None:
    a = [1.0, 0.0]
    b = [-1.0, 0.0]
    # raw cosine = -1 → shifted to 0.0
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_orthogonal_vectors() -> None:
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    # raw cosine = 0 → shifted to 0.5
    assert cosine_similarity(a, b) == pytest.approx(0.5)


def test_cosine_zero_vector_returns_zero() -> None:
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_cosine_result_in_unit_interval() -> None:
    import random
    rng = random.Random(42)
    for _ in range(20):
        a = [rng.gauss(0, 1) for _ in range(8)]
        b = [rng.gauss(0, 1) for _ in range(8)]
        sim = cosine_similarity(a, b)
        assert 0.0 <= sim <= 1.0


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


def test_provider_satisfies_protocol() -> None:
    provider = _make_provider()
    assert isinstance(provider, SemanticSimilarityProvider)


# ---------------------------------------------------------------------------
# Happy-path compute (mocked HTTP)
# ---------------------------------------------------------------------------


def test_compute_returns_valid_semantic_score() -> None:
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [0.9, 0.1, 0.0]

    provider = _make_provider()

    call_count = 0

    def fake_post(url, json, headers):
        nonlocal call_count
        call_count += 1
        text = json["input"]
        # Return different vectors for different texts
        vec = vec_a if "person" in text else vec_b
        return _mock_embedding_response(vec)

    with patch("packages.suggestions.semantic.azure_openai_provider.httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.post.side_effect = fake_post
        MockClient.return_value = mock_client_instance

        score = provider.compute(
            _desc("person", "person_id", "unique patient identifier"),
            _desc("Patient", "id", "logical resource id"),
        )

    assert 0.0 <= score.similarity <= 1.0
    assert score.explanation
    assert "azure" in score.explanation.lower() or "openai" in score.explanation.lower()


# ---------------------------------------------------------------------------
# Caching — API called once per unique text
# ---------------------------------------------------------------------------


def test_embedding_is_cached() -> None:
    provider = _make_provider()
    vec = [0.5, 0.5, 0.0]

    call_count = [0]

    def fake_post(url, json, headers):
        call_count[0] += 1
        return _mock_embedding_response(vec)

    with patch("packages.suggestions.semantic.azure_openai_provider.httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.post.side_effect = fake_post
        MockClient.return_value = mock_client_instance

        # Same descriptors twice → text is identical → should only call API once per text
        desc = _desc("person", "person_id")
        provider.compute(desc, desc)
        provider.compute(desc, desc)

    # Both source and target have the same text; even on first call only one
    # API request should be made (cached after first embed).
    assert call_count[0] == 1
    assert provider.cache_size == 1


def test_clear_cache_resets_cache() -> None:
    provider = _make_provider()
    vec = [1.0, 0.0]
    call_count = [0]

    def fake_post(url, json, headers):
        call_count[0] += 1
        return _mock_embedding_response(vec)

    with patch("packages.suggestions.semantic.azure_openai_provider.httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.post.side_effect = fake_post
        MockClient.return_value = mock_client_instance

        desc = _desc("obs", "value")
        provider.compute(desc, desc)
        assert provider.cache_size == 1

        provider.clear_cache()
        assert provider.cache_size == 0

        provider.compute(desc, desc)

    # After clearing, the same text should trigger a new API call.
    assert call_count[0] == 2


# ---------------------------------------------------------------------------
# Fallback on API error
# ---------------------------------------------------------------------------


def test_falls_back_to_lexical_on_http_error() -> None:
    provider = _make_provider()

    with patch("packages.suggestions.semantic.azure_openai_provider.httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.post.side_effect = Exception("connection refused")
        MockClient.return_value = mock_client_instance

        score = provider.compute(
            _desc("person", "birth_date"),
            _desc("Patient", "birthDate"),
        )

    # Must not raise; must return a valid score with fallback explanation.
    assert 0.0 <= score.similarity <= 1.0
    assert "connection refused" in score.explanation.lower() or "exception" in score.explanation.lower()


def test_fallback_explanation_mentions_error_type() -> None:
    provider = _make_provider()

    with patch("packages.suggestions.semantic.azure_openai_provider.httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client_instance.post.side_effect = TimeoutError("timed out")
        MockClient.return_value = mock_client_instance

        score = provider.compute(
            _desc("obs", "code"),
            _desc("Observation", "code"),
        )

    # The explanation should mention it fell back and the error type.
    assert "TimeoutError" in score.explanation or "fallback" in score.explanation.lower()


# ---------------------------------------------------------------------------
# build_semantic_provider factory
# ---------------------------------------------------------------------------


def test_build_returns_lexical_when_env_vars_absent(monkeypatch) -> None:
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", raising=False)

    provider = build_semantic_provider()
    assert isinstance(provider, LexicalSemanticProvider)


def test_build_returns_azure_when_env_vars_set(monkeypatch) -> None:
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", _ENDPOINT)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", _API_KEY)
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", _DEPLOYMENT)

    provider = build_semantic_provider()
    assert isinstance(provider, AzureOpenAIEmbeddingProvider)


def test_build_returns_lexical_when_only_partial_env(monkeypatch) -> None:
    """Missing any one required var → fallback to lexical."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", _ENDPOINT)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", _API_KEY)
    monkeypatch.delenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", raising=False)

    provider = build_semantic_provider()
    assert isinstance(provider, LexicalSemanticProvider)
