"""FAQ knowledge-base search implementation.

Implements a simple, dependency-free relevance search over a local list of
:class:`~student_support_assistance.models.FAQEntry` records, combining token
(Jaccard) overlap with sequence-based similarity so that both keyword
matches and near-duplicate phrasings score well.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from student_support_assistance import config
from student_support_assistance.data import KNOWLEDGE_BASE
from student_support_assistance.models import FAQEntry, FAQSearchResult, KnowledgeBaseError
from student_support_assistance.utils import require_non_empty_string, tokenize


def _entry_tokens(entry: FAQEntry) -> set[str]:
    """Build the searchable token set for a single FAQ entry.

    Args:
        entry: The FAQ entry to tokenize.

    Returns:
        A set of lowercase tokens drawn from the question, answer, and tags.
    """
    tokens = tokenize(entry.question) | tokenize(entry.answer)
    tokens.update(tag.lower() for tag in entry.tags)
    return tokens


def _score_entry(query: str, query_tokens: set[str], entry: FAQEntry) -> float:
    """Score how relevant an FAQ entry is to a search query.

    Combines Jaccard token overlap (captures keyword matches) with a
    sequence-similarity ratio against the question text (captures
    near-duplicate phrasings), so scores fall in ``[0.0, 1.0]``.

    Args:
        query: The raw, lowercased query string.
        query_tokens: Tokenized form of the query.
        entry: The FAQ entry being scored.

    Returns:
        A relevance score between 0.0 and 1.0.
    """
    entry_tokens = _entry_tokens(entry)
    union = query_tokens | entry_tokens
    jaccard = len(query_tokens & entry_tokens) / len(union) if union else 0.0
    sequence_ratio = SequenceMatcher(None, query, entry.question.lower()).ratio()
    return (config.JACCARD_WEIGHT * jaccard) + (config.SEQUENCE_WEIGHT * sequence_ratio)


def search_faqs(
    query: str,
    top_k: int = config.TOP_K_RESULTS,
    knowledge_base: tuple[FAQEntry, ...] = KNOWLEDGE_BASE,
) -> list[FAQSearchResult]:
    """Search the FAQ knowledge base and return the most relevant entries.

    Args:
        query: The user's search text. Must be a non-empty string.
        top_k: Maximum number of results to return.
        knowledge_base: The FAQ entries to search, injectable for testing.

    Returns:
        Up to ``top_k`` :class:`FAQSearchResult` instances, sorted by
        descending relevance score. Entries scoring below
        :data:`config.MIN_RELEVANCE_SCORE` are excluded.

    Raises:
        InvalidInputError: If ``query`` is not a string.
        EmptyQueryError: If ``query`` is empty or whitespace-only.
        KnowledgeBaseError: If the knowledge base itself is empty.
    """
    clean_query = require_non_empty_string(query, "query")
    if not knowledge_base:
        raise KnowledgeBaseError("The knowledge base is empty; cannot search.")

    lowered_query = clean_query.lower()
    query_tokens = tokenize(clean_query)

    scored = [
        FAQSearchResult(question=entry.question, answer=entry.answer, score=score)
        for entry in knowledge_base
        if (score := round(_score_entry(lowered_query, query_tokens, entry), 4))
        >= config.MIN_RELEVANCE_SCORE
    ]
    scored.sort(key=lambda result: result.score, reverse=True)
    return scored[:top_k]
