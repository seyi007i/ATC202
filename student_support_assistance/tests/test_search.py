"""Tests for the FAQ knowledge-base search implementation."""

from __future__ import annotations

import pytest

from student_support_assistance import config
from student_support_assistance.knowledge_base import search_faqs
from student_support_assistance.models import (
    EmptyQueryError,
    FAQEntry,
    InvalidInputError,
    KnowledgeBaseError,
)


class TestSearchFaqsHappyPath:
    """Tests covering normal, successful search behavior."""

    def test_returns_at_most_top_k_results(self) -> None:
        """A broad query should return no more than TOP_K_RESULTS entries."""
        results = search_faqs("tuition payment deadline")
        assert len(results) <= config.TOP_K_RESULTS

    def test_results_sorted_by_descending_score(self) -> None:
        """Returned results must be sorted from most to least relevant."""
        results = search_faqs("When is course registration?")
        scores = [result.score for result in results]
        assert scores == sorted(scores, reverse=True)

    def test_exact_question_match_scores_highly(self) -> None:
        """A query matching an FAQ question verbatim should rank first."""
        results = search_faqs("When is course registration?")
        assert results
        assert "registration" in results[0].question.lower()

    def test_scores_within_valid_range(self) -> None:
        """Every returned score must fall within [0.0, 1.0]."""
        results = search_faqs("graduation requirements")
        assert all(0.0 <= result.score <= 1.0 for result in results)

    def test_tuition_query_finds_tuition_faq(self) -> None:
        """A tuition-focused query should surface a tuition-related FAQ."""
        results = search_faqs("How much is tuition and how do I pay it?")
        assert any("tuition" in result.question.lower() for result in results)

    def test_respects_custom_top_k(self) -> None:
        """Passing a smaller top_k should limit the number of results."""
        results = search_faqs("payment tuition deadline registration", top_k=1)
        assert len(results) == 1


class TestSearchFaqsErrorHandling:
    """Tests covering invalid input and edge cases."""

    def test_empty_string_raises_empty_query_error(self) -> None:
        """An empty string query must raise EmptyQueryError."""
        with pytest.raises(EmptyQueryError):
            search_faqs("")

    def test_whitespace_only_raises_empty_query_error(self) -> None:
        """A whitespace-only query must raise EmptyQueryError."""
        with pytest.raises(EmptyQueryError):
            search_faqs("   \t\n  ")

    @pytest.mark.parametrize("bad_query", [None, 123, 3.14, ["tuition"], {"q": "x"}])
    def test_non_string_query_raises_invalid_input_error(self, bad_query: object) -> None:
        """Non-string queries of various types must raise InvalidInputError."""
        with pytest.raises(InvalidInputError):
            search_faqs(bad_query)  # type: ignore[arg-type]

    def test_empty_query_error_is_an_invalid_input_error(self) -> None:
        """EmptyQueryError should be catchable as InvalidInputError too."""
        with pytest.raises(InvalidInputError):
            search_faqs("")

    def test_nonsense_query_returns_low_or_no_results(self) -> None:
        """A query unrelated to any FAQ should return few or no matches."""
        results = search_faqs("xyzzy quantum flibbertigibbet")
        assert len(results) <= config.TOP_K_RESULTS

    def test_empty_knowledge_base_raises_knowledge_base_error(self) -> None:
        """Searching an empty knowledge base must raise KnowledgeBaseError."""
        with pytest.raises(KnowledgeBaseError):
            search_faqs("tuition", knowledge_base=())

    def test_injected_knowledge_base_is_used(self) -> None:
        """A custom knowledge base passed in should be searched instead of
        the default one."""
        custom = (
            FAQEntry(question="Do robots dream?", answer="Only in fiction.", tags=("robots",)),
        )
        results = search_faqs("robots dreaming", knowledge_base=custom)
        assert results
        assert results[0].question == "Do robots dream?"
