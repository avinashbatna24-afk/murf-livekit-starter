"""
tools.py — Day 5 Live Tools for EduVoice

Provides two capabilities:
  1. fetch_practice_question: Fetches a live MCQ from Open Trivia DB (opentdb.com)
     mapped to the student's subject and class level. Falls back to a hand-built
     local question bank when the API is unavailable.
  2. score_student_answer: Scores the student's spoken answer against the correct
     answer locally (no API needed).

Data source: https://opentdb.com (live, no API key required, CC BY-SA 4.0)
Fallback: hand-built local dataset of 5 questions per subject.
"""

import html
import logging
import random
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger("agent.tools")

OPENTDB_BASE_URL = "https://opentdb.com/api.php"
OPENTDB_TIMEOUT_SECONDS = 5.0

# Subject name → Open Trivia DB category ID
SUBJECT_TO_CATEGORY: dict[str, int] = {
    "maths": 19,
    "math": 19,
    "mathematics": 19,
    "science": 17,
    "biology": 17,
    "physics": 17,
    "chemistry": 17,
    "computers": 18,
    "computer": 18,
    "coding": 18,
    "python": 18,
    "programming": 18,
    "history": 23,
    "geography": 22,
    "gk": 9,
    "general knowledge": 9,
}

# Class level → Open Trivia DB difficulty
LEVEL_TO_DIFFICULTY: dict[str, str] = {
    "class 6": "easy",
    "class 7": "easy",
    "class 8": "easy",
    "class 9": "medium",
    "class 10": "medium",
    "class 11": "hard",
    "class 12": "hard",
    "degree": "hard",
    "college": "hard",
    "easy": "easy",
    "medium": "medium",
    "hard": "hard",
}

# Fallback local question bank (used when API is unreachable)
# Format: {subject: [{question, correct_answer, choices: [A,B,C,D]}]}
FALLBACK_QUESTIONS: dict[str, list[dict]] = {
    "maths": [
        {
            "question": "What is the value of pi, rounded to two decimal places?",
            "correct_answer": "3.14",
            "choices": ["3.14", "2.17", "3.41", "1.73"],
        },
        {
            "question": "What is the square root of 144?",
            "correct_answer": "12",
            "choices": ["11", "12", "13", "14"],
        },
        {
            "question": "If 2x + 5 = 13, what is x?",
            "correct_answer": "4",
            "choices": ["3", "4", "5", "6"],
        },
    ],
    "science": [
        {
            "question": "Which gas do plants absorb from the air during photosynthesis?",
            "correct_answer": "Carbon dioxide",
            "choices": ["Oxygen", "Carbon dioxide", "Nitrogen", "Hydrogen"],
        },
        {
            "question": "What is the chemical formula for water?",
            "correct_answer": "H2O",
            "choices": ["CO2", "H2O", "NaCl", "O2"],
        },
        {
            "question": "What force keeps planets in orbit around the Sun?",
            "correct_answer": "Gravity",
            "choices": ["Magnetism", "Friction", "Gravity", "Electricity"],
        },
    ],
    "computers": [
        {
            "question": "What does CPU stand for?",
            "correct_answer": "Central Processing Unit",
            "choices": [
                "Central Processing Unit",
                "Computer Personal Unit",
                "Central Program Utility",
                "Control Processing Unit",
            ],
        },
        {
            "question": "Which programming language is known for its use with data science?",
            "correct_answer": "Python",
            "choices": ["Java", "C++", "Python", "HTML"],
        },
    ],
    "history": [
        {
            "question": "In which year did India gain independence?",
            "correct_answer": "1947",
            "choices": ["1945", "1947", "1950", "1952"],
        },
        {
            "question": "Who was the first Prime Minister of India?",
            "correct_answer": "Jawaharlal Nehru",
            "choices": [
                "Mahatma Gandhi",
                "Jawaharlal Nehru",
                "Sardar Patel",
                "B.R. Ambedkar",
            ],
        },
    ],
    "geography": [
        {
            "question": "What is the capital city of India?",
            "correct_answer": "New Delhi",
            "choices": ["Mumbai", "Kolkata", "New Delhi", "Chennai"],
        },
        {
            "question": "Which is the longest river in India?",
            "correct_answer": "Ganga",
            "choices": ["Yamuna", "Godavari", "Ganga", "Krishna"],
        },
    ],
    "gk": [
        {
            "question": "What is the national animal of India?",
            "correct_answer": "Bengal Tiger",
            "choices": ["Lion", "Elephant", "Bengal Tiger", "Peacock"],
        },
        {
            "question": "How many states are there in India?",
            "correct_answer": "28",
            "choices": ["26", "27", "28", "29"],
        },
    ],
}


def _normalize_subject(subject: str) -> str:
    """Normalize subject string to a key used in our mappings."""
    return subject.strip().lower()


def _get_difficulty(level: str) -> str:
    """Map student level string to API difficulty. Defaults to 'medium'."""
    level_lower = level.strip().lower()
    # Direct key match
    if level_lower in LEVEL_TO_DIFFICULTY:
        return LEVEL_TO_DIFFICULTY[level_lower]
    # Partial match (e.g. "Class 10 Math" → "class 10")
    for key, diff in LEVEL_TO_DIFFICULTY.items():
        if key in level_lower:
            return diff
    return "medium"


def _get_fallback(subject_key: str) -> Optional[dict]:
    """Return a random question from the local fallback bank for a given subject."""
    bank = FALLBACK_QUESTIONS.get(subject_key)
    if not bank:
        # Try a broader match
        for key in FALLBACK_QUESTIONS:
            if key in subject_key or subject_key in key:
                bank = FALLBACK_QUESTIONS[key]
                break
    if not bank:
        bank = FALLBACK_QUESTIONS["gk"]  # Last resort: general knowledge
    return random.choice(bank)


async def fetch_practice_question(
    subject: str,
    level: str = "Class 10",
) -> dict:
    """
    Fetch a live multiple-choice question from Open Trivia DB for the given subject
    and student level. Returns a dict with:
      - question (str)
      - correct_answer (str)
      - choices (list[str])
      - difficulty (str)
      - source (str): 'live' or 'local'
      - fetched_at (str): ISO timestamp in UTC

    Falls back to a hand-built local question if the API is unavailable.
    """
    subject_key = _normalize_subject(subject)
    category_id = SUBJECT_TO_CATEGORY.get(subject_key)

    # Try broader match if exact key not found
    if not category_id:
        for key, cat_id in SUBJECT_TO_CATEGORY.items():
            if key in subject_key or subject_key in key:
                category_id = cat_id
                subject_key = key
                break

    difficulty = _get_difficulty(level)
    fetched_at = datetime.now(timezone.utc).isoformat()

    # --- Attempt live API call ---
    if category_id:
        params = {
            "amount": 1,
            "category": category_id,
            "difficulty": difficulty,
            "type": "multiple",
        }
        try:
            async with httpx.AsyncClient(timeout=OPENTDB_TIMEOUT_SECONDS) as client:
                response = await client.get(OPENTDB_BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            if data.get("response_code") == 0 and data.get("results"):
                result = data["results"][0]
                # Decode HTML entities (API returns &amp; etc.)
                question_text = html.unescape(result["question"])
                correct = html.unescape(result["correct_answer"])
                incorrect = [html.unescape(a) for a in result["incorrect_answers"]]

                # Shuffle choices so correct answer isn't always last
                choices = [*incorrect, correct]
                random.shuffle(choices)

                logger.info(
                    "Fetched live question from Open Trivia DB: subject=%s difficulty=%s",
                    subject,
                    difficulty,
                )
                return {
                    "question": question_text,
                    "correct_answer": correct,
                    "choices": choices,
                    "difficulty": difficulty,
                    "source": "live",
                    "fetched_at": fetched_at,
                }
            else:
                logger.warning(
                    "Open Trivia DB returned no results: code=%s",
                    data.get("response_code"),
                )

        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as e:
            logger.warning("Open Trivia DB unreachable, using fallback: %s", e)
        except Exception as e:
            logger.error("Unexpected error fetching from Open Trivia DB: %s", e)

    # --- Fallback to local question bank ---
    logger.info("Using local fallback question for subject=%s", subject_key)
    fallback = _get_fallback(subject_key)
    return {
        "question": fallback["question"],
        "correct_answer": fallback["correct_answer"],
        "choices": fallback["choices"],
        "difficulty": difficulty,
        "source": "local",
        "fetched_at": fetched_at,
    }


def score_student_answer(student_answer: str, correct_answer: str) -> dict:
    """
    Score the student's spoken answer against the correct answer.
    Returns a dict with:
      - is_correct (bool)
      - student_answer (str)
      - correct_answer (str)
      - feedback (str): short spoken feedback for the agent to say
    """
    # Normalize both answers for comparison
    student_clean = student_answer.strip().lower()
    correct_clean = correct_answer.strip().lower()

    # Exact match
    is_correct = student_clean == correct_clean

    # Partial/contained match (handles "the answer is 12" → "12")
    if not is_correct:
        is_correct = correct_clean in student_clean or student_clean in correct_clean

    feedback = (
        f"Super! Correct answer brother! '{correct_answer}' — bilkul sahi!"
        if is_correct
        else f"Chinna mistake brother. Correct answer is '{correct_answer}'. Em problem ledu, try chedam!"
    )

    logger.info(
        "Scored answer: student='%s' correct='%s' result=%s",
        student_answer,
        correct_answer,
        is_correct,
    )
    return {
        "is_correct": is_correct,
        "student_answer": student_answer,
        "correct_answer": correct_answer,
        "feedback": feedback,
    }
