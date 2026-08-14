"""
tests/test_tools.py — Day 5 tests for fetch_practice_question and score_student_answer.

Tests:
  1. Live API call succeeds and returns correct structure
  2. Graceful local fallback when API is mocked to be unreachable
  3. Subject-to-category mapping for key subjects
  4. Level-to-difficulty mapping
  5. score_student_answer correct match
  6. score_student_answer partial match (student says more than the answer)
  7. score_student_answer wrong answer
"""

from unittest.mock import AsyncMock, patch

import pytest

from tools import (
    SUBJECT_TO_CATEGORY,
    _get_difficulty,
    fetch_practice_question,
    score_student_answer,
)

# ---------------------------------------------------------------------------
# score_student_answer tests (synchronous, no network)
# ---------------------------------------------------------------------------


def test_score_exact_correct():
    result = score_student_answer("Carbon dioxide", "Carbon dioxide")
    assert result["is_correct"] is True
    assert "కరెక్ట్" in result["feedback"] or "Correct" in result["feedback"]


def test_score_case_insensitive():
    result = score_student_answer("carbon dioxide", "Carbon dioxide")
    assert result["is_correct"] is True


def test_score_partial_match():
    # Student says a sentence containing the answer
    result = score_student_answer("I think the answer is 12", "12")
    assert result["is_correct"] is True


def test_score_wrong_answer():
    result = score_student_answer("Oxygen", "Carbon dioxide")
    assert result["is_correct"] is False
    assert (
        "మిస్టేక్" in result["feedback"]
        or "mistake" in result["feedback"].lower()
        or "Correct answer" in result["feedback"]
    )


def test_score_returns_correct_answer_in_feedback():
    result = score_student_answer("Oxygen", "Carbon dioxide")
    assert "Carbon dioxide" in result["feedback"]


# ---------------------------------------------------------------------------
# Mapping tests
# ---------------------------------------------------------------------------


def test_subject_mapping_maths():
    assert SUBJECT_TO_CATEGORY.get("maths") == 19
    assert SUBJECT_TO_CATEGORY.get("math") == 19
    assert SUBJECT_TO_CATEGORY.get("mathematics") == 19


def test_subject_mapping_science():
    assert SUBJECT_TO_CATEGORY.get("science") == 17
    assert SUBJECT_TO_CATEGORY.get("biology") == 17


def test_subject_mapping_computers():
    assert SUBJECT_TO_CATEGORY.get("computers") == 18
    assert SUBJECT_TO_CATEGORY.get("python") == 18


def test_level_difficulty_class10():
    assert _get_difficulty("Class 10") == "medium"
    assert _get_difficulty("class 10 math") == "medium"


def test_level_difficulty_class12():
    assert _get_difficulty("Class 12") == "hard"


def test_level_difficulty_class7():
    assert _get_difficulty("Class 7") == "easy"


def test_level_difficulty_default():
    assert _get_difficulty("unknown grade") == "medium"


# ---------------------------------------------------------------------------
# fetch_practice_question — live API call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_live_question_structure():
    """Test that a live API call returns the expected structure."""
    result = await fetch_practice_question(subject="Science", level="Class 10")
    assert "question" in result
    assert "correct_answer" in result
    assert "choices" in result
    assert len(result["choices"]) == 4
    assert "difficulty" in result
    assert result["difficulty"] == "medium"
    assert "source" in result
    assert result["source"] in ("live", "local")
    assert "fetched_at" in result


@pytest.mark.asyncio
async def test_fetch_live_question_maths():
    result = await fetch_practice_question(subject="Maths", level="Class 9")
    assert "question" in result
    assert result["difficulty"] == "medium"


# ---------------------------------------------------------------------------
# fetch_practice_question — graceful fallback when API is unreachable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fallback_when_api_unreachable():
    """When httpx raises a network error, we should fall back to local questions."""
    import httpx

    with patch("tools.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.NetworkError("No internet"))
        mock_client_class.return_value = mock_client

        result = await fetch_practice_question(subject="Science", level="Class 10")

    assert result["source"] == "local"
    assert "question" in result
    assert "correct_answer" in result
    assert len(result["choices"]) >= 2


@pytest.mark.asyncio
async def test_fallback_when_api_timeout():
    """When httpx times out, we should fall back to local questions."""
    import httpx

    with patch("tools.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client_class.return_value = mock_client

        result = await fetch_practice_question(subject="History", level="Class 8")

    assert result["source"] == "local"
    assert "question" in result


@pytest.mark.asyncio
async def test_fallback_for_unknown_subject():
    """Unknown subject falls back to GK questions without crashing."""
    result = await fetch_practice_question(subject="Astrology", level="Class 9")
    # Either live (if API has something) or local — should not raise
    assert "question" in result
    assert "correct_answer" in result
