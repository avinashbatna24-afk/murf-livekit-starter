"""
tools.py — Day 5 Live Tools for EduVoice

Provides two capabilities:
  1. fetch_practice_question: Generates a topic-specific MCQ via Google Gemini
     when a discussion topic is known (e.g. "Photosynthesis"), OR fetches a
     subject-level MCQ from Open Trivia DB (opentdb.com) when no specific topic
     is given. Falls back to a hand-built local question bank if both fail.
  2. score_student_answer: Scores the student's spoken answer against the correct
     answer locally (no API needed).

Data sources (in priority order):
  1. Google Gemini API — topic-specific MCQ generation (requires GOOGLE_API_KEY)
  2. Open Trivia DB — subject-level random questions (free, no key)
  3. Hand-built local question bank — fallback when both APIs are unavailable
"""

import html
import json
import logging
import os
import random
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger("agent.tools")

OPENTDB_BASE_URL = "https://opentdb.com/api.php"
OPENTDB_TIMEOUT_SECONDS = 5.0
GEMINI_TIMEOUT_SECONDS = 8.0
GEMINI_TOPIC_MODEL = "gemini-1.5-flash-latest"

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


async def _generate_topic_question_via_gemini(
    topic: str,
    difficulty: str,
    fetched_at: str,
) -> Optional[dict]:
    """
    Ask Google Gemini to generate a single multiple-choice question specifically
    about the given topic. Returns a structured dict or None if it fails.
    """
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning(
            "GOOGLE_API_KEY not set, cannot generate topic question via Gemini"
        )
        return None

    prompt = (
        f"Generate exactly ONE multiple-choice question about '{topic}' "
        f"at {difficulty} difficulty for a high school student in India.\n\n"
        "Respond ONLY with a valid JSON object in this exact format (no extra text):\n"
        '{"question": "...", "correct_answer": "...", "incorrect_answers": ["...", "...", "..."]}'
    )

    gemini_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_TOPIC_MODEL}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 300,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=GEMINI_TIMEOUT_SECONDS) as client:
            response = await client.post(gemini_url, json=payload)
            response.raise_for_status()
            data = response.json()

        raw_text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        parsed = json.loads(raw_text)
        question_text = parsed["question"]
        correct = parsed["correct_answer"]
        incorrect = parsed["incorrect_answers"][:3]

        choices = [*incorrect, correct]
        random.shuffle(choices)

        logger.info(
            "Generated topic-specific question via Gemini: topic='%s' difficulty=%s",
            topic,
            difficulty,
        )
        return {
            "question": question_text,
            "correct_answer": correct,
            "choices": choices,
            "difficulty": difficulty,
            "source": "gemini-topic",
            "fetched_at": fetched_at,
        }

    except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as e:
        logger.warning("Gemini API unreachable for topic question: %s", e)
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.warning("Failed to parse Gemini response for topic question: %s", e)
    except Exception as e:
        logger.error("Unexpected error generating topic question via Gemini: %s", e)

    return None


async def fetch_practice_question(
    subject: str,
    level: str = "Class 10",
    topic: Optional[str] = None,
) -> dict:
    """
    Fetch or generate a multiple-choice practice question for the student.

    Priority order:
      1. If `topic` is given: generate a question about that specific topic
         using Google Gemini (e.g. "Photosynthesis", "Quadratic Equations").
      2. If no topic or Gemini fails: fetch a subject-level random question
         from Open Trivia DB.
      3. If Open Trivia DB also fails: use the hand-built local question bank.

    Returns a dict with:
      - question (str)
      - correct_answer (str)
      - choices (list[str])
      - difficulty (str)
      - source (str): 'gemini-topic', 'live', or 'local'
      - fetched_at (str): ISO timestamp in UTC

    Falls back to a hand-built local question if all APIs are unavailable.
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

    # --- PRIORITY 1: Topic-specific question via Gemini ---
    if topic and topic.strip():
        topic_clean = topic.strip()
        gemini_result = await _generate_topic_question_via_gemini(
            topic=topic_clean, difficulty=difficulty, fetched_at=fetched_at
        )
        if gemini_result:
            return gemini_result
        logger.info("Gemini topic question failed, falling back to Open Trivia DB")

    # --- PRIORITY 2: Open Trivia DB (subject-level) ---
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

    # --- PRIORITY 3: Local fallback question bank ---
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
