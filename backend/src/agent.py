import logging
import asyncio

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    tokenize,
    room_io,
)
from livekit.plugins import murf, silero, google, deepgram
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# Change this prompt to change what your voice agent does.
# See README.md for example prompts (customer support, language tutor, receptionist).
SYSTEM_PROMPT = """
IDENTITY

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
- Always write Telugu words in simple English script so TTS pronounces it smoothly.
- Keep technical terms and subject words in English (e.g. "Photosynthesis", "Python loop", "Quadratic equation").

TEACHING & EVALUATION FLOW (CRITICAL)

1. When explaining a topic: Explain simply in Tenglish and offer a quick practice question to test them.
2. When student attempts the answer:
   - If CORRECT: Praise them warmly ("Super brother! Absolutely correct answer!").
   - If INCORRECT: Politely and gently correct them in friendly Tenglish without making them feel bad (e.g., "Chinna mistake brother, em kadhu! Correct answer is... Arthamaindha?").
3. AFTER evaluating/correcting their answer:
   Always ask politely: "Shall we do another practice question, or do you want any other topic to get cleared?" ("Inko question cheddama, leda inko topic clear cheskundama?")

KNOWLEDGE & SCOPE

You teach Mathematics, Science, Computer Science (Java, Python, C, C++), English, and General Knowledge.

STYLE CONSTRAINTS

- ALWAYS speak in Telugu-English mix (Tenglish using English script).
- Keep sentences short, spoken, and energetic (under 40 words per response).
"""

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def my_agent(ctx: JobContext):
    # Connect to the LiveKit room immediately to prevent timeouts
    await ctx.connect()

    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using Deepgram (Telugu STT), Gemini (LLM), Murf Falcon (TTS)
    session = AgentSession(
        stt=deepgram.STT(
            model="nova-3",
            language="multi",
        ),
        llm=google.LLM(
            model="gemini-flash-latest",
        ),
        tts=murf.TTS(
            voice="Abhinav",
            locale="en-IN",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=1),
            text_pacing=True
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        min_endpointing_delay=0.1,
        max_endpointing_delay=0.8,
        preemptive_generation=True,
    )

    # Start the session, which initializes the voice pipeline
    await session.start(
        agent=Assistant(),
        room=ctx.room,
    )

    participant = await ctx.wait_for_participant()

    # Greet the student as soon as they join
    await session.generate_reply(
        instructions="""
        Greet the student warmly in natural Telugu-English mix (Tenglish using English script).
        Example: "Namaste! Nenu EduVoice, mee AI learning tutor. Eeroju em subject or topic nerchukundam?"
        Keep it friendly and under 30 words.
        """
    )

    # await asyncio.sleep(4)

#     await session.generate_reply(
#     instructions="""
#     Greet the student warmly.

#     Introduce yourself as EduVoice.

#     Tell them they can speak in Telugu, English, or Telugu-English.

#     Mention that you help students learn Science, Maths,
#     Programming and English.

#     Keep it under 35 words.
#     """
# )

if __name__ == "__main__":
    cli.run_app(server)
