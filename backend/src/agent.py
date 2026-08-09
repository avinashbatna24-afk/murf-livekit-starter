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

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# System prompt for EduVoice Voice Tutor with Persistent Memory & Consent Rules
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
- Keep technical terms and subject words in English (e.g. "Photosynthesis", "Python loop", "Quadratic equation").

HARD RULE 1: CONSENT BEFORE SAVING DATA (CRITICAL FOR DAY 4)

- You have a memory tool: `save_user_memory(user_id, name, language_preference, facts)`.
- YOU MUST NEVER SAVE DATA AUTOMATICALLY WITHOUT ASKING FIRST.
- After teaching a topic or before ending a turn/session, YOU MUST ASK THE CALLER:
  "Mee details & nerchukunna topics memory lo save cheskona next call kosam? Is it okay to save this?"
- EVALUATE THE USER'S RESPONSE:
  • IF USER SAYS YES ("Yes", "Sare", "Okay", "Save it", "Sure"):
    Call `save_user_memory(user_id=..., name=..., language_preference='Tenglish', facts={...})` and confirm to user: "Super! Mee details save chesenu brother."
  • IF USER SAYS NO ("No", "Voddhu", "Don't save", "Never mind", "No thanks"):
    DO NOT CALL `save_user_memory`. Drop the data immediately and confirm: "Sare brother, no problem! Data em save cheyaledhu."

HARD RULE 2: FORGET ME TOOL

- If the caller requests to wipe or delete their memory ("Forget me", "Delete my data", "Nanu marchipo"), invoke `forget_user_memory(user_id)` and confirm deletion: "Done brother! Mee records anni delete chesenu."

HARD RULE 3: RETRIEVING MEMORY

- You have tool `lookup_user_memory(user_id)`. Use it if you need to fetch saved facts about a caller.

FACTS STRUCTURE FOR LEARNING & LITERACY TRACK:
- `current_level`: Class / Grade level (e.g., "Class 10 Math").
- `topics_covered`: List of topics discussed (e.g., ["Quadratic Equations", "Photosynthesis"]).
- `mistakes_made`: Short note on areas needing practice (e.g., "Minus sign calculation error").

TEACHING & EVALUATION FLOW:
1. Explain topics simply in Tenglish and offer a quick practice question.
2. Evaluate responses warmly ("Super brother! Absolutely correct answer!" or "Chinna mistake brother, correct answer is...").
3. Always check if they want another practice question or new topic, or ask for consent to save their progress.

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
