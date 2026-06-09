"""Default deterministic semantic-similarity provider for v1.

Algorithm
---------
LexicalSemanticProvider implements similarity as a **weighted combination of
three deterministic text signals**, all operating on the normalised
``SemanticDescriptor.semantic_text`` strings.  No ML or network calls are made.

Signal 1 — Jaccard token overlap (weight 0.50)
    Tokenise both semantic texts on whitespace/separators, compute
    |intersection| / |union|.  Rewards shared vocabulary across table names,
    field names, and descriptions.

Signal 2 — Longest Common Subsequence ratio (weight 0.30)
    LCS length / max(len(a), len(b)) computed on the *token lists* (not
    characters).  Rewards partial-order agreement of shared tokens, e.g.
    "care site name" vs "organisation site name" → LCS = ["site", "name"].

Signal 3 — Field-name exact / prefix match bonus (weight 0.20)
    +1.0 if normalised field names are identical.
    +0.5 if one normalised field name is a prefix of the other.
    0.0 otherwise.
    This boosts pairs like (patient_id, person_id) that share a suffix/domain
    concept but differ in table vocabulary.

All weights are configurable via the constructor.

Normalisation (shared with strategies.py conventions)
------------------------------------------------------
* Swedish characters → ASCII (å→a, ä→a, ö→o, etc.)
* NFC unicode normalisation
* Lowercase
* Split on ``[_.\-/\s]+``
* Rejoin with space for semantic text; keep as list for LCS
"""

from __future__ import annotations

import re
import unicodedata
from typing import List

from packages.suggestions.semantic.interface import (
    SemanticDescriptor,
    SemanticScore,
)

# ---------------------------------------------------------------------------
# Internal normalisation helpers
# ---------------------------------------------------------------------------

_SWEDISH: dict[str, str] = {
    "å": "a", "ä": "a", "ö": "o",
    "Å": "A", "Ä": "A", "Ö": "O",
}
_SEP_RE = re.compile(r"[_.\-/\s]+")


def _normalize(text: str) -> str:
    for src, dst in _SWEDISH.items():
        text = text.replace(src, dst)
    text = unicodedata.normalize("NFC", text).lower()
    return text


def _tokenize(text: str) -> List[str]:
    """Normalize and split into tokens, filtering empty strings."""
    return [t for t in _SEP_RE.split(_normalize(text)) if t]


def _jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    union = sa | sb
    if not union:
        return 0.0
    return len(sa & sb) / len(union)


def _lcs_length(a: List[str], b: List[str]) -> int:
    """Longest Common Subsequence length on token lists (DP, O(m*n))."""
    m, n = len(a), len(b)
    if m == 0 or n == 0:
        return 0
    # Use O(n) space rolling array
    prev = [0] * (n + 1)
    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(curr[j - 1], prev[j])
        prev = curr
    return prev[n]


def _lcs_ratio(a: List[str], b: List[str]) -> float:
    denom = max(len(a), len(b))
    if denom == 0:
        return 0.0
    return _lcs_length(a, b) / denom


def _field_name_bonus(src_name: str, tgt_name: str) -> float:
    """Compute a bonus score based on field-name similarity."""
    sn = _normalize(src_name)
    tn = _normalize(tgt_name)
    if sn == tn:
        return 1.0
    # Prefix match (either direction)
    if sn.startswith(tn) or tn.startswith(sn):
        return 0.5
    # Shared suffix (common pattern: patient_id / person_id share "_id")
    src_parts = _SEP_RE.split(sn)
    tgt_parts = _SEP_RE.split(tn)
    if src_parts and tgt_parts and src_parts[-1] == tgt_parts[-1]:
        return 0.3
    return 0.0


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class LexicalSemanticProvider:
    """Deterministic lexical semantic-similarity provider (v1 default).

    Computes a weighted combination of Jaccard token overlap, LCS token ratio,
    and a field-name exact/prefix bonus.  Produces a human-readable explanation
    describing which signals contributed and what vocabulary was shared.

    Args:
        jaccard_weight:     Weight of Jaccard token overlap signal (default 0.50).
        lcs_weight:         Weight of LCS token ratio signal (default 0.30).
        field_name_weight:  Weight of field-name exact/prefix bonus (default 0.20).

    The three weights must sum to 1.0 (validated on construction).
    """

    def __init__(
        self,
        jaccard_weight: float = 0.50,
        lcs_weight: float = 0.30,
        field_name_weight: float = 0.20,
    ) -> None:
        total = jaccard_weight + lcs_weight + field_name_weight
        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                f"LexicalSemanticProvider weights must sum to 1.0; got {total}"
            )
        self._w_jaccard = jaccard_weight
        self._w_lcs = lcs_weight
        self._w_field = field_name_weight

    def compute(
        self,
        source: SemanticDescriptor,
        target: SemanticDescriptor,
    ) -> SemanticScore:
        """Compute lexical semantic similarity between two field descriptors.

        Returns a SemanticScore whose ``explanation`` describes the dominant
        signal and any shared vocabulary found.
        """
        src_tokens = _tokenize(source.semantic_text)
        tgt_tokens = _tokenize(target.semantic_text)

        jaccard = _jaccard(src_tokens, tgt_tokens)
        lcs = _lcs_ratio(src_tokens, tgt_tokens)
        field_bonus = _field_name_bonus(source.field_name, target.field_name)

        composite = round(
            self._w_jaccard * jaccard
            + self._w_lcs * lcs
            + self._w_field * field_bonus,
            4,
        )

        # Build explanation
        shared_vocab = sorted(set(src_tokens) & set(tgt_tokens))
        explanation = _build_explanation(
            source=source,
            target=target,
            jaccard=jaccard,
            lcs=lcs,
            field_bonus=field_bonus,
            composite=composite,
            shared_vocab=shared_vocab,
        )

        return SemanticScore(similarity=composite, explanation=explanation)


# ---------------------------------------------------------------------------
# Explanation builder
# ---------------------------------------------------------------------------


def _build_explanation(
    source: SemanticDescriptor,
    target: SemanticDescriptor,
    jaccard: float,
    lcs: float,
    field_bonus: float,
    composite: float,
    shared_vocab: List[str],
) -> str:
    """Produce a human-readable explanation of the semantic similarity score."""
    if composite >= 0.9:
        quality = "strong"
    elif composite >= 0.6:
        quality = "moderate"
    elif composite >= 0.3:
        quality = "weak"
    else:
        quality = "low"

    parts: List[str] = []

    if field_bonus >= 1.0:
        parts.append(
            f"Exact field-name match ('{source.field_name}' == '{target.field_name}')"
        )
    elif field_bonus >= 0.5:
        parts.append(
            f"Field-name prefix overlap ('{source.field_name}' / '{target.field_name}')"
        )
    elif field_bonus >= 0.3:
        parts.append(
            f"Shared field-name suffix ('{source.field_name}' / '{target.field_name}')"
        )

    if shared_vocab:
        # Highlight domain-relevant vocabulary (skip generic stopwords)
        _STOP = {"of", "the", "a", "an", "in", "for", "and", "or", "is", "to"}
        domain_terms = [t for t in shared_vocab if t not in _STOP]
        if domain_terms:
            parts.append(
                f"Shared semantic vocabulary: {', '.join(domain_terms[:6])}"
            )

    if jaccard >= 0.5:
        parts.append(
            f"High token overlap between "
            f"'{source.table_name}.{source.field_name}' and "
            f"'{target.table_name}.{target.field_name}' "
            f"(Jaccard={jaccard:.2f})"
        )
    elif jaccard > 0:
        parts.append(
            f"Partial token overlap "
            f"(Jaccard={jaccard:.2f})"
        )

    if not parts:
        parts.append(
            f"Low semantic similarity between "
            f"'{source.table_name}.{source.field_name}' and "
            f"'{target.table_name}.{target.field_name}'"
        )

    # Prefix with domain context when table names differ
    if _normalize(source.table_name) != _normalize(target.table_name):
        context = (
            f"Semantic similarity ({quality}) based on "
            f"{source.table_name} → {target.table_name} context"
        )
    else:
        context = f"Semantic similarity ({quality}) within '{source.table_name}'"

    detail = "; ".join(parts)
    return f"{context}: {detail}."
