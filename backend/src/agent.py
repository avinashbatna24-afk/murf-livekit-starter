import json
import logging

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    tokenize,
)
from livekit.plugins import deepgram, google, murf, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from db import delete_user_memory, get_user_memory, init_db, save_user_memory
from tools import fetch_practice_question, score_student_answer

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# System prompt for EduVoice Voice Tutor — Day 5: Live Tools + Persistent Memory
SYSTEM_PROMPT = """
IDENTITY & ROLE

You are EduVoice, a native Telugu AI Voice Tutor built for Indian students for VoiceForBharat.
You talk like a friendly, enthusiastic, local Telugu brother/teacher who makes learning super fun and easy!

PERSONA & NATIVE TELUGU TONE

- Talk like a genuine local Telugu guy (conversational, warm, empathetic).
- Use natural Telugu expressions:
  • "Namaste brother / sister!"
  • "Chala simple concept idhi!"
  • "Em ledu, simple ga cheppalante..."
  • "Super cheppav!"
  • "Chinna mistake brother, em kadhu vinu..."
  • "Arthamaindha?"
- Always write Telugu words in simple English script (Tenglish) so TTS pronounces it smoothly.
- Keep technical terms in English (e.g. "Photosynthesis", "Python loop", "Quadratic equation").

DAY 5 TOOL RULES — LIVE QUIZ QUESTIONS

You have TWO live tools for fetching and scoring practice questions:

TOOL A: `fetch_practice_question(subject, level)`
- Call this whenever a student asks for a practice question, quiz, or exercise on any subject.
- Examples that MUST trigger this tool:
  • "Give me a Science question" → fetch_practice_question(subject='Science', level='Class 10')
  • "Oka Maths question iyyi" → fetch_practice_question(subject='Maths', level='Class 9')
  • "Quiz cheyyi" (any subject) → fetch_practice_question(subject=<infer from context>, level=<from memory or ask>)
- CHAIN WITH DAY 4 MEMORY: If you already know the student's `current_level` from memory, use it automatically — DO NOT ask again.
- After fetching, SPEAK the question naturally in Tenglish. State if the data is live:
  • source='live': "Ee question internet nundi live ga vasindi!"
  • source='local': "Internet lo chinna issue, so naa local question ista!"
- Give the student multiple choice options A, B, C, D — read them aloud.
- Wait for the student's answer before calling score_student_answer.

TOOL B: `score_student_answer(student_answer, correct_answer)`
- Call this IMMEDIATELY after the student responds with their answer to the quiz question.
- Pass exactly what the student said and the correct answer from the fetched question.
- Use the returned `feedback` to respond to the student.
- After scoring, update `topics_covered` and `mistakes_made` in your context for memory saving.

FAILURE HANDLING:
- If fetch_practice_question returns source='local', say: "Internet lo chinna problem, but no worries! Local question ista."
- Never go silent. Never invent a question. Always speak a result.

DAY 4 MEMORY RULES

HARD RULE 1 — CONSENT BEFORE SAVING:
- Tool: `save_user_memory(user_id, name, language_preference, facts)`
- NEVER save without asking first. After teaching, ask:
  "Mee details & nerchukunna topics memory lo save cheskona next call kosam? Is it okay?"
- YES ("Yes", "Sare", "Okay", "Sure"): call `save_user_memory`, confirm: "Super! Mee details save chesenu brother."
- NO ("No", "Voddhu", "Don't save"): drop data, confirm: "Sare brother, no problem! Data em save cheyaledhu."

HARD RULE 2 — FORGET ME:
- If caller says "Forget me" / "Delete my data" / "Nanu marchipo": call `forget_user_memory(user_id)`, confirm: "Done! Mee records delete chesenu brother."

HARD RULE 3 — RETRIEVE MEMORY:
- Tool: `lookup_user_memory(user_id)` — use it to fetch saved facts about a returning caller.

FACTS STRUCTURE:
- `current_level`: Class / Grade (e.g., "Class 10 Math")
- `topics_covered`: List of topics (e.g., ["Photosynthesis", "Quadratic Equations"])
- `mistakes_made`: Areas to improve (e.g., "Minus sign errors")

TEACHING & EVALUATION FLOW:
1. Explain topics simply in Tenglish, then offer to fetch a live practice question.
2. Fetch question → ask student → score with score_student_answer → give warm feedback.
3. Ask if they want another question or new topic, then ask consent to save progress.

STYLE CONSTRAINTS:
- ALWAYS speak in Telugu-English mix (Tenglish using English script).
- Keep responses short, spoken, and energetic (under 40 words per response).
"""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

    @function_tool
    async def lookup_user_memory(self, context: RunContext, user_id: str) -> str:
        """Look up saved memory and facts for a caller by user_id.

        Args:
            user_id: The unique ID or username of the caller.
        """
        memory = get_user_memory(user_id)
        if not memory:
            return f"No saved memory record found for user ID '{user_id}'."
        return json.dumps(memory)

    @function_tool
    async def save_user_memory(
        self,
        context: RunContext,
        user_id: str,
        name: str,
        language_preference: str,
        facts: dict,
    ) -> str:
        """Save or update caller memory and facts in the SQLite database.

        CRITICAL: YOU MUST ALWAYS ASK THE CALLER FOR EXPLICIT PERMISSION BEFORE EXECUTING THIS TOOL.
        Only call this if the user answered 'Yes' or explicitly consented to saving their progress.

        Args:
            user_id: The unique ID or username of the caller.
            name: The caller's name.
            language_preference: Preferred language (e.g., 'Tenglish', 'English', 'Telugu').
            facts: Dictionary containing 'current_level', 'topics_covered', 'mistakes_made'.
        """
        saved = save_user_memory(
            user_id=user_id,
            name=name,
            language_preference=language_preference,
            facts=facts,
        )
        logger.info("Executed save_user_memory tool for %s (%s)", name, user_id)
        return f"Successfully saved user memory for {name} ({user_id}): {json.dumps(saved)}"

    @function_tool
    async def forget_user_memory(self, context: RunContext, user_id: str) -> str:
        """Permanently delete caller memory from the database if requested by the caller.

        Args:
            user_id: The unique ID or username of the caller.
        """
        deleted = delete_user_memory(user_id)
        if deleted:
            logger.info("Executed forget_user_memory tool for user_id=%s", user_id)
            return f"Memory record for user ID '{user_id}' has been permanently wiped."
        return f"No memory record was found to delete for user ID '{user_id}'."

    @function_tool
    async def fetch_practice_question(
        self,
        context: RunContext,
        subject: str,
        level: str = "Class 10",
    ) -> str:
        """Fetch a live multiple-choice practice question from the internet for a student.

        WHEN TO CALL: Call this whenever the student asks for a practice question, quiz,
        exercise, or says things like "Give me a question", "Oka question iyyi",
        "Quiz cheyyi", "Practice chesdam".

        CHAINING WITH MEMORY: If you already know the student's current_level from memory,
        pass it as 'level' automatically without asking again.

        DATA SOURCE: Questions come live from Open Trivia DB (opentdb.com).
        If the API is unavailable, a local fallback question is returned instead.
        Always tell the student whether the question came live or from local backup.

        Args:
            subject: The subject for the question (e.g. 'Science', 'Maths', 'History',
                     'Computers', 'Geography', 'GK'). Infer from context if not stated.
            level: The student's class or level (e.g. 'Class 10', 'Class 8', 'hard').
                   Use the student's saved current_level from memory if available.
        """
        logger.info(
            "fetch_practice_question called: subject=%s level=%s", subject, level
        )
        result = await fetch_practice_question(subject=subject, level=level)

        choices_labeled = ""
        labels = ["A", "B", "C", "D"]
        for i, choice in enumerate(result["choices"][:4]):
            choices_labeled += f"\n  {labels[i]}) {choice}"

        source_note = (
            "[DATA SOURCE: Live from Open Trivia DB (opentdb.com) — fetched just now]"
            if result["source"] == "live"
            else "[DATA SOURCE: Local fallback question bank (API unavailable)]"
        )
        fetched_at = result["fetched_at"]

        return (
            f"{source_note}\n"
            f"Fetched at: {fetched_at} UTC\n"
            f"Subject: {subject} | Difficulty: {result['difficulty']}\n\n"
            f"QUESTION: {result['question']}\n"
            f"CHOICES:{choices_labeled}\n\n"
            f"CORRECT_ANSWER (do NOT reveal yet): {result['correct_answer']}\n\n"
            "Instructions: Read the question and choices aloud naturally in Tenglish. "
            "Wait for student answer. Then call score_student_answer with their response "
            f"and correct_answer='{result['correct_answer']}'"
        )

    @function_tool
    async def score_student_answer(
        self,
        context: RunContext,
        student_answer: str,
        correct_answer: str,
    ) -> str:
        """Score the student's spoken answer to a quiz question.

        WHEN TO CALL: Call this immediately after the student responds to a quiz question
        that was fetched by fetch_practice_question. Pass exactly what the student said
        and the correct answer from the fetched question.

        After calling this, use the returned 'feedback' to respond to the student warmly
        in Tenglish. Update topics_covered and mistakes_made in your memory context.

        Args:
            student_answer: Exactly what the student said as their answer.
            correct_answer: The correct answer from the previously fetched question.
        """
        logger.info(
            "score_student_answer called: student='%s' correct='%s'",
            student_answer,
            correct_answer,
        )
        result = score_student_answer(
            student_answer=student_answer, correct_answer=correct_answer
        )
        return (
            f"SCORING RESULT:\n"
            f"  Student answered: '{result['student_answer']}'\n"
            f"  Correct answer: '{result['correct_answer']}'\n"
            f"  Is correct: {result['is_correct']}\n"
            f"  Feedback to speak: {result['feedback']}\n\n"
            "Use the feedback above to respond to the student in Tenglish. "
            "If incorrect, note the topic in mistakes_made for memory saving."
        )


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    init_db()


server.setup_fnc = prewarm


@server.rtc_session()
async def my_agent(ctx: JobContext):
    # Connect to LiveKit room immediately
    await ctx.connect()

    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Make sure DB is initialized
    init_db()

    # Retrieve caller participant identity
    participant = await ctx.wait_for_participant()
    user_id = (participant.identity or "student_1").strip().lower()
    raw_name = participant.name or participant.identity or "student"

    # Async memory lookup for returning user
    user_mem = get_user_memory(user_id)

    # Set up voice AI session
    session = AgentSession(
        stt=deepgram.STT(
            model="nova-3",
            language="multi",
        ),
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),
        tts=murf.TTS(
            voice="Abhinav",
            locale="en-IN",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=1),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        min_endpointing_delay=0.1,
        max_endpointing_delay=0.8,
        preemptive_generation=True,
    )

    await session.start(
        agent=Assistant(),
        room=ctx.room,
    )

    if user_mem:
        caller_name = user_mem.get("name") or raw_name
        facts = user_mem.get("facts", {})
        topics = facts.get("topics_covered", "your previous lessons")
        if isinstance(topics, list):
            topics = ", ".join(topics)

        greeting_instruction = f"""
        RETURNING CALLER FOUND!
        User ID: '{user_id}'
        Caller Name: '{caller_name}'
        Saved Facts: {json.dumps(facts)}

        Greet {caller_name} warmly in Tenglish (English script).
        Example: "Namaste {caller_name}! Last time we discussed {topics}. Welcome back brother! Eeroju em topic nerchukundam?"
        Keep greeting friendly, natural, and under 30 words.
        """
    else:
        caller_name = raw_name.title() if raw_name else "Student"
        greeting_instruction = f"""
        NEW CALLER JOINED!
        User ID: '{user_id}'
        Name: '{caller_name}'

        Greet {caller_name} warmly as EduVoice, their AI learning tutor.
        Example: "Namaste {caller_name}! Nenu EduVoice, mee AI tutor. Eeroju em subject or topic nerchukundam?"
        Keep greeting friendly, welcoming, and under 30 words.
        """

    await session.generate_reply(instructions=greeting_instruction)


if __name__ == "__main__":
    cli.run_app(server)
