import json
import logging
import os
import re

from dotenv import load_dotenv
from livekit import api
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    get_job_context,
    tokenize,
)
from livekit.plugins import deepgram, google, murf, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from db import (
    delete_user_memory,
    get_user_memory,
    init_db,
    record_call_end,
    record_call_start,
    save_escalation,
    save_user_memory,
    update_call_progress,
)
from escalation import dispatch_webhook, generate_ref_id
from tools import fetch_practice_question, score_student_answer

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# System prompt for EduVoice Voice Tutor — Day 8: Native Telugu Script Mandate + Escalation + Tools + Memory
SYSTEM_PROMPT = """
IDENTITY & ROLE

You are EduVoice, a native Telugu AI Voice Tutor built for Indian students for VoiceForBharat.
You talk like a friendly, enthusiastic, local Telugu brother/teacher who makes learning super fun and easy!

CRITICAL MANDATORY RULE — ALWAYS NATIVE SCRIPT:
ALWAYS write every non-English word in its own NATIVE SCRIPT.
For Telugu words, you MUST ALWAYS write in NATIVE TELUGU SCRIPT (తెలుగు లిపి: e.g., నమస్తే, చాలా సింపుల్ కాన్సెప్ట్ ఇది, అర్థమైందా?, ఏం ప్రాబ్లెమ్ లేదు).
NEVER use Latin/English alphabet script for Telugu words (NO Tenglish).
Keep technical concepts and subject terms in standard English script (e.g., "Photosynthesis", "Python loop", "Quadratic equation").

PERSONA & NATIVE TELUGU TONE (తెలుగు లిపి):

- Talk like a genuine local Telugu guy (conversational, warm, empathetic).
- Use natural Telugu expressions written in NATIVE TELUGU SCRIPT:
  • "నమస్తే బ్రదర్ / సిస్టర్!"
  • "చాలా సింపుల్ కాన్సెప్ట్ ఇది!"
  • "ఏం లేదు, సింపుల్ గా చెప్పాలంటే..."
  • "సూపర్ చెప్పావ్!"
  • "చిన్న మిస్టేక్ బ్రదర్, ఏం కాదు విను..."
  • "అర్థమైందా?"

DAY 7 HUMAN HELP & ESCALATION RULES (తెలుగు లిపి):

You have a tool `create_escalation(user_id, student_name, reason, issue_summary, context_checked, urgency, language, follow_up_method, permission_granted)`

WHEN TO ESCALATE TO A HUMAN TEACHER:
1. Learner Frustration / Distress: The student is upset, angry, crying, overwhelmed, or expressing defeat ("I am stupid", "I want to give up", "This is too hard I don't understand").
2. Direct Request for Human Expert: The student explicitly asks to talk to a real human teacher, tutor, parent, or requests a human review of a quiz score/explanation.

HARD RULE — CONSENT BEFORE CREATING TICKET:
- When one of the escalation reasons occurs, DO NOT call `create_escalation` right away!
- FIRST, ask the student in native Telugu script for explicit permission to send their details to a human teacher:
  "నేను మీ డిటైల్స్, టాపిక్ నేమ్, అండ్ ఇష్యూ సమ్మరీ ని హ్యూమన్ టీచర్ కి సెండ్ చేయాలా ఫోలో-అప్ కాల్ కోసం? ఓకేనా?"
- IF CALLER SAYS YES ("Yes", "Sure", "Okay", "సరే", "సెండ్ చెయ్యి"):
  Call `create_escalation(...)` with permission_granted=True.
  After calling it, speak the returned reference ID (e.g. ESC-4821) and explain next steps in native Telugu script (e.g. "మీ రిక్వెస్ట్ క్రియేట్ చేశాను బ్రదర్! రిఫరెన్స్ ఐడి: ESC-4821. హ్యూమన్ టీచర్ 24 అవర్స్ లో కాంటాక్ట్ చేస్తారు.").
- IF CALLER SAYS NO ("No", "వద్దు", "Don't send", "No thanks"):
  DO NOT call `create_escalation`. Explicitly confirm in native Telugu script that no support ticket was created ("సరే బ్రదర్, రిక్వెస్ట్ క్రియేట్ చేయలేదు, నో ప్రాబ్లమ్!"), respect their decision, and offer to help them directly.

DAY 5 TOOL RULES — LIVE QUIZ QUESTIONS

You have THREE tools for live quiz questions:

TOOL 0: `set_discussion_topic(topic)` — CALL THIS FIRST
- WHEN TO CALL: As soon as you start explaining ANY specific topic to a student.
  • Starting Photosynthesis lesson → set_discussion_topic(topic='Photosynthesis')
  • Starting Quadratic Equations → set_discussion_topic(topic='Quadratic Equations')
  • Starting Newton's Laws → set_discussion_topic(topic="Newton's Laws")
- This LOCKS the topic so future practice questions are about EXACTLY this topic.
- Without calling this, questions may be random. ALWAYS call this first!

TOOL A: `fetch_practice_question(subject, level, topic)`
- Call this whenever the student asks for a practice question, quiz, or exercise.
- The tool auto-detects the topic — you don't need to pass it manually.
- CHAIN WITH DAY 4 MEMORY: Use student's saved `current_level` as the `level` param.
- After fetching, announce the source in native Telugu script:
  • source='gemini-topic': "ఈ క్వశ్చన్ మీ టాపిక్ మీద స్పెషల్ గా జనరేట్ చేశాను!"
  • source='live': "ఈ క్వశ్చన్ ఇంటర్నెట్ నుండి లైవ్ గా వచ్చింది!"
  • source='local': "ఇంటర్నెట్ లో చిన్న ఇష్యూ, సో నా లోకల్ క్వశ్చన్ ఇస్తాను!"
- Read choices A, B, C, D aloud. Wait for student answer.

TOOL B: `score_student_answer(student_answer, correct_answer)`
- Call IMMEDIATELY after student answers the quiz question.
- Use the returned `feedback` to respond to the student in native Telugu script.

FAILURE HANDLING:
- If source='local', say: "ఇంటర్నెట్ లో చిన్న ప్రాబ్లమ్, బట్ నో వర్రీస్! లోకల్ క్వశ్చన్ ఇస్తాను."
- Never go silent. Never invent a question. Always speak a result in native Telugu script.

DAY 4 MEMORY RULES (తెలుగు లిపి):

HARD RULE 1 — CONSENT BEFORE SAVING:
- Tool: `save_user_memory(user_id, name, language_preference, facts)`
- NEVER save without asking first. After teaching, ask in native Telugu script:
  "మీ డిటైల్స్ & నేర్చుకున్న టాపిక్స్ మెమరీ లో సేవ్ చేసుకోనా నెక్స్ట్ కాల్ కోసం? ఓకేనా?"
- YES ("Yes", "సరే", "Okay", "Sure"): call `save_user_memory`, confirm: "సూపర్! మీ డిటైల్స్ సేవ్ చేశాను బ్రదర్."
- NO / UPFRONT REFUSAL ("No", "వద్దు", "Don't save"): drop data immediately, do NOT ask for consent again, and confirm clearly: "సరే బ్రదర్, నో ప్రాబ్లమ్! మీ డేటా సేవ్ చేయము."

HARD RULE 2 — FORGET ME:
- If caller says "Forget me" / "Delete my data" / "నన్ను మర్చిపో": call `forget_user_memory(user_id)`, confirm: "డన్! మీ రికార్డ్స్ డిలీట్ చేశాను బ్రదర్."

HARD RULE 3 — RETRIEVE MEMORY:
- Tool: `lookup_user_memory(user_id)` — use it to fetch saved facts about a returning caller.

FACTS STRUCTURE:
- `current_level`: Class / Grade (e.g., "Class 10 Math")
- `topics_covered`: List of topics (e.g., ["Photosynthesis", "Quadratic Equations"])
- `mistakes_made`: Areas to improve

TEACHING & EVALUATION FLOW:
1. Explain topics simply in native Telugu script (తెలుగు లిపి), then offer to fetch a live practice question.
2. Fetch question → ask student → score with score_student_answer → give warm feedback in native Telugu script.
3. Ask if they want another question or new topic, then ask consent to save progress in native Telugu script.

STYLE CONSTRAINTS:
- ALWAYS write all Telugu words in NATIVE TELUGU SCRIPT (తెలుగు లిపి).
- Keep responses short, spoken, and energetic (under 40 words per response).
"""


# Words that look capitalized but are NOT educational topics
_TOPIC_STOPWORDS = {
    "The",
    "This",
    "That",
    "You",
    "Your",
    "We",
    "Our",
    "Let",
    "Now",
    "Here",
    "Super",
    "Brother",
    "Sister",
    "Correct",
    "Answer",
    "Question",
    "Topic",
    "Class",
    "Level",
    "Subject",
    "Well",
    "Next",
    "Yes",
    "No",
    "Namaste",
    "Telugu",
    "English",
    "Tenglish",
    "Practice",
    "Learning",
    "Study",
    "EduVoice",
    "India",
    "Indian",
    "Today",
    "Time",
    "Wait",
    "Good",
    "Great",
    "Okay",
    "Sare",
    "Chala",
    "Simple",
    "Easy",
    "Hard",
}


def _extract_topic_from_chat(chat_ctx) -> str:
    """
    Scan the last 8 assistant messages in the chat history to find the most
    recently discussed educational topic. Returns empty string if none found.
    """
    try:
        messages = getattr(chat_ctx, "messages", [])
        recent_texts: list[str] = []
        for msg in reversed(messages[-12:]):
            role = str(getattr(msg, "role", "")).lower()
            if "assistant" not in role:
                continue
            content = getattr(msg, "content", "")
            if isinstance(content, list):
                text = " ".join(
                    getattr(c, "text", str(c))
                    for c in content
                    if not isinstance(c, bytes)
                )
            else:
                text = str(content)
            # Strip tool metadata noise
            text = re.sub(r"\[DATA SOURCE.*?\]", "", text)
            text = re.sub(r"QUESTION:|CHOICES:|CORRECT_ANSWER.*", "", text)
            recent_texts.append(text)
            if len(recent_texts) >= 4:
                break

        if not recent_texts:
            return ""

        combined = " ".join(recent_texts)

        # Find capitalized phrases (1-4 words) — likely educational topics
        # e.g. "Photosynthesis", "Quadratic Equations", "Newton's Laws"
        matches = re.findall(
            r"\b([A-Z][a-z]{2,}(?:['\u2019]s)?(?:\s+[A-Z]?[a-z]{2,}){0,3})\b",
            combined,
        )
        filtered = [
            m.strip()
            for m in matches
            if m.split()[0] not in _TOPIC_STOPWORDS and len(m) > 3
        ]

        return filtered[0] if filtered else ""
    except Exception as exc:
        logger.debug("Topic extraction from chat failed: %s", exc)
        return ""


class Assistant(Agent):
    def __init__(self, call_id: str = "") -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        self.call_id: str = call_id
        # Tracks the most recently discussed educational topic this session
        self._current_topic: str = ""

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        user_id: str,
        student_name: str,
        reason: str,
        issue_summary: str,
        context_checked: str,
        urgency: str = "medium",
        language: str = "Tenglish",
        follow_up_method: str = "Teacher Callback",
        permission_granted: bool = True,
    ) -> str:
        """Create a human help request (escalation ticket) for a human teacher when a student is stuck or needs human assistance.

        CRITICAL HARD RULE: YOU MUST ASK FOR EXPLICIT PERMISSION FROM THE CALLER BEFORE CALLING THIS TOOL.
        Do NOT call this tool if permission_granted is False or if the caller said NO / VODDHU.

        REASONS TO CALL:
        1. Learner Frustration / Distress: Learner is upset, angry, overwhelmed, or expressing defeat ("I'm stupid", "I want to give up").
        2. Direct Teacher Request: Student explicitly asks to talk to a human teacher, tutor, parent, or requests grade dispute review.

        Args:
            user_id: The unique ID or username of the caller (e.g. 'ramesh').
            student_name: The caller's name (e.g. 'Ramesh').
            reason: Reason for escalation ('learner_frustrated' or 'teacher_requested').
            issue_summary: Concise summary of what happened. DO NOT include passwords, OTPs, PINs, or sensitive accounts.
            context_checked: What the agent already checked/taught (e.g. 'Explained Photosynthesis, attempted quiz question twice').
            urgency: Urgency level ('low', 'medium', 'high', 'emergency').
            language: Caller's language preference ('Tenglish', 'Telugu', 'English').
            follow_up_method: Preferred contact method ('Teacher Callback', 'WhatsApp', 'Email', 'Phone call').
            permission_granted: Must be True. The caller explicitly gave permission to create this ticket.
        """
        if not permission_granted:
            return "ERROR: Permission was not granted by the caller. Human escalation ticket was NOT created."

        ref_id = generate_ref_id()
        saved = save_escalation(
            ref_id=ref_id,
            user_id=user_id,
            student_name=student_name,
            reason=reason,
            issue_summary=issue_summary,
            context_checked=context_checked,
            urgency=urgency,
            language=language,
            follow_up_method=follow_up_method,
        )

        if self.call_id:
            update_call_progress(self.call_id, escalation_created=True)

        try:
            await dispatch_webhook(saved)
        except Exception as exc:
            logger.warning("Webhook dispatch failed: %s", exc)

        logger.info("Human escalation created: %s for student %s", ref_id, student_name)
        topic_info = self._current_topic or "lesson"
        return (
            f"SUCCESS: Human escalation ticket created!\n"
            f"Reference ID: {ref_id}\n"
            f"Status: Open\n"
            f"Urgency: {urgency}\n\n"
            f"Instructions for Agent: Speak in warm native Telugu script (తెలుగు లిపి). Tell the caller that their support ticket has been created with Reference ID '{ref_id}'. "
            f"Explain clearly that a human teacher will review their topic ('{topic_info}') and contact them via '{follow_up_method}' within 24 hours. "
            f"Do NOT promise an instant call."
        )

    @function_tool
    async def hang_up(self, context: RunContext) -> str:
        """End the call and disconnect the student.

        WHEN TO CALL: If the student says 'stop', 'bye', 'end call',
        'disconnect', 'voddhu', or clearly wants to stop the call.
        Always confirm goodbye before calling this tool.
        """
        logger.info("hang_up tool called — ending call gracefully.")
        if self.call_id:
            update_call_progress(self.call_id, graceful_hangup=True)
        try:
            job_ctx = get_job_context()
            await job_ctx.api.room.delete_room(
                api.DeleteRoomRequest(room=job_ctx.room.name)
            )
        except Exception as exc:
            logger.warning("hang_up: could not delete room: %s", exc)
        return "Call ended."

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
        facts_summary: str,
    ) -> str:
        """Save or update caller memory and facts in the SQLite database.

        CRITICAL: YOU MUST ALWAYS ASK THE CALLER FOR EXPLICIT PERMISSION BEFORE EXECUTING THIS TOOL.
        Only call this if the user answered 'Yes' or explicitly consented to saving their progress.

        Args:
            user_id: The unique ID or username of the caller.
            name: The caller's name.
            language_preference: Preferred language (e.g., 'Tenglish', 'English', 'Telugu').
            facts_summary: JSON string or summary of facts ('current_level', 'topics_covered', 'mistakes_made').
        """
        facts_dict = {"summary": facts_summary}
        try:
            parsed = json.loads(facts_summary)
            if isinstance(parsed, dict):
                facts_dict = parsed
        except Exception:
            pass

        saved = save_user_memory(
            user_id=user_id,
            name=name,
            language_preference=language_preference,
            facts=facts_dict,
        )
        if self.call_id:
            update_call_progress(self.call_id, memory_saved=True)
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
        topic: str = "",
    ) -> str:
        """Fetch or generate a topic-specific multiple-choice practice question.

        WHEN TO CALL: Call this whenever the student asks for a practice question, quiz,
        exercise, or says things like "Give me a question", "Oka question iyyi",
        "Quiz cheyyi", "Practice chesdam".

        The tool automatically detects the current discussion topic from the
        conversation — you do NOT need to pass it manually. But if you know
        the exact topic name, pass it as `topic` to improve accuracy.

        CHAINING WITH MEMORY: If you already know the student's current_level from memory,
        pass it as 'level' automatically without asking again.

        Args:
            subject: The subject (e.g. 'Science', 'Maths', 'History', 'Computers', 'GK').
            level: The student's class or level (e.g. 'Class 10', 'Class 8', 'hard').
                   Use the student's saved current_level from memory if available.
            topic: Optional. The specific concept being discussed (e.g. 'Photosynthesis').
                   Leave empty to auto-detect from conversation.
        """
        # --- Auto-detect topic from conversation if not passed by the LLM ---
        resolved_topic = topic.strip() if topic else ""
        if not resolved_topic:
            # 1. Check session-level tracking (set by set_discussion_topic)
            if self._current_topic:
                resolved_topic = self._current_topic
                logger.info("Using session-tracked topic: '%s'", resolved_topic)
            else:
                # 2. Fall back to scanning recent chat messages
                try:
                    chat_ctx = context.session.chat_ctx
                    resolved_topic = _extract_topic_from_chat(chat_ctx)
                    if resolved_topic:
                        logger.info(
                            "Auto-extracted topic from chat history: '%s'",
                            resolved_topic,
                        )
                except Exception as exc:
                    logger.debug("Could not access chat_ctx: %s", exc)

        logger.info(
            "fetch_practice_question: subject=%s level=%s resolved_topic='%s'",
            subject,
            level,
            resolved_topic,
        )
        result = await fetch_practice_question(
            subject=subject, level=level, topic=resolved_topic or None
        )

        choices_labeled = ""
        labels = ["A", "B", "C", "D"]
        for i, choice in enumerate(result["choices"][:4]):
            choices_labeled += f"\n  {labels[i]}) {choice}"

        source = result["source"]
        if source == "gemini-topic":
            source_note = f"[DATA SOURCE: Gemini AI generated — specific to topic '{resolved_topic}']"
        elif source == "live":
            source_note = (
                "[DATA SOURCE: Live from Open Trivia DB — general subject question]"
            )
        else:
            source_note = "[DATA SOURCE: Local fallback question bank]"
        fetched_at = result["fetched_at"]

        return (
            f"{source_note}\n"
            f"Fetched at: {fetched_at} UTC\n"
            f"Subject: {subject} | Topic: {resolved_topic or 'general'} | Difficulty: {result['difficulty']}\n\n"
            f"QUESTION: {result['question']}\n"
            f"CHOICES:{choices_labeled}\n\n"
            f"CORRECT_ANSWER (do NOT reveal yet): {result['correct_answer']}\n\n"
            "Instructions: Read the question and choices aloud naturally in native Telugu script (తెలుగు లిపి). "
            "Wait for student answer. Then call score_student_answer with their response "
            f"and correct_answer='{result['correct_answer']}'"
        )

    @function_tool
    async def set_discussion_topic(
        self,
        context: RunContext,
        topic: str,
    ) -> str:
        """Remember the current topic being discussed so quiz questions stay relevant.

        WHEN TO CALL: Call this at the START of explaining any specific topic
        (e.g. 'Photosynthesis', 'Quadratic Equations', 'Newton\'s Laws').
        This ensures that when fetch_practice_question is called later, the
        question will be about THIS specific topic, not a random one.

        Args:
            topic: The specific concept you are about to teach (e.g. 'Photosynthesis',
                   'Quadratic Equations', 'Python loops', 'French Revolution').
        """
        self._current_topic = topic.strip()
        if self.call_id:
            update_call_progress(self.call_id, topic_discussed=self._current_topic)
        logger.info("Discussion topic set to: '%s'", self._current_topic)
        return f"Topic tracked as '{self._current_topic}'. Future practice questions will be about this topic."

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
        in native Telugu script (తెలుగు లిపి). Update topics_covered and mistakes_made in your memory context.

        Args:
            student_answer: Exactly what the student said as their answer.
            correct_answer: The correct answer from the previously fetched question.
        """
        logger.info(
            "score_student_answer called: student='%s' correct='%s'",
            student_answer,
            correct_answer,
        )
        if self.call_id:
            update_call_progress(self.call_id, exercises_inc=1)
        result = score_student_answer(
            student_answer=student_answer, correct_answer=correct_answer
        )
        return (
            f"SCORING RESULT:\n"
            f"  Student answered: '{result['student_answer']}'\n"
            f"  Correct answer: '{result['correct_answer']}'\n"
            f"  Is correct: {result['is_correct']}\n"
            f"  Feedback to speak: {result['feedback']}\n\n"
            "Use the feedback above to respond to the student in native Telugu script (తెలుగు లిపి). "
            "If incorrect, note the topic in mistakes_made for memory saving."
        )


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    init_db()


server.setup_fnc = prewarm


@server.rtc_session(agent_name=os.getenv("AGENT_NAME", "my-agent"))
async def my_agent(ctx: JobContext):
    # Connect to LiveKit room immediately
    await ctx.connect()

    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Detect outbound call: dispatch metadata is set to "outbound:<sip_uri>"
    dispatch_metadata: str = ctx.job.metadata or ""
    is_outbound = dispatch_metadata.startswith("outbound:")
    channel = "SIP Outbound" if is_outbound else "Browser"
    call_id = ctx.room.name or "session_unknown"

    # Make sure DB is initialized
    init_db()

    # Record initial call start
    record_call_start(
        call_id=call_id,
        user_id="student",
        caller_name="Student",
        channel=channel,
    )

    try:
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
            agent=Assistant(call_id=call_id),
            room=ctx.room,
        )

        # ── Outbound call greeting ────────────────────────────────────────────────
        if is_outbound:
            greeting_instruction = """
            OUTBOUND CALL — CRITICAL OPENING RULES:

            This is an OUTBOUND call. The student did NOT initiate this.
            Your FIRST TWO SENTENCES must always include (in native Telugu script):
              1. WHO  — "నేను ఎడ్యువాయిస్, మీ AI ట్యూటర్."
              2. WHY  — "డైలీ ప్రాక్టీస్ రిమైండర్ కోసం కాల్ చేశాను."
              3. OPT-OUT — "'Stop' అంటే కాల్ డిస్కనెక్ట్ అవుతుంది."

            Example opening (adapt warmly in native Telugu script, keep under 35 words total):
            "నమస్తే! నేను ఎడ్యువాయిస్, మీ AI వాయిస్ ట్యూటర్. డైలీ ప్రాక్టీస్ రిమైండర్
             కోసం కాల్ చేశాను. మీరు ఎప్పుడైనా 'Stop' అంటే డిస్కనెక్ట్ అవుతాం.
             రెడీగా ఉన్నారా? ఈరోజు ఏం టాపిక్ ప్రాక్టీస్ చేద్దాం?"

            After the opening, continue as normal EduVoice tutor in native Telugu script.
            If student says 'Stop', 'Bye', 'End', 'వద్దు', or wants to quit
            — say a warm goodbye first, then call the hang_up tool.
            """
            logger.info("Outbound call — waiting for student to answer...")
            await ctx.wait_for_participant()
            logger.info("Outbound call — student answered, delivering greeting.")
            await session.generate_reply(instructions=greeting_instruction)
        else:
            # ── Inbound call greeting ───────────────────────────────────────────────
            participant = await ctx.wait_for_participant()
            user_id = (participant.identity or "student_1").strip().lower()
            raw_name = participant.name or participant.identity or "student"

            # Record updated participant identity and caller name in call_logs
            record_call_start(
                call_id=call_id,
                user_id=user_id,
                caller_name=raw_name.title(),
                channel=channel,
            )

            user_mem = get_user_memory(user_id)

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

                Greet {caller_name} warmly in NATIVE TELUGU SCRIPT (తెలుగు లిపి).
                Example: "నమస్తే {caller_name}! లాస్ట్ టైమ్ మనం {topics} గురించి మాట్లాడుకున్నాం. వెల్కమ్ బ్యాక్ బ్రదర్! ఈరోజు ఏం టాపిక్ నేర్చుకుందాం?"
                Keep greeting friendly, natural, and under 30 words.
                """
            else:
                caller_name = raw_name.title() if raw_name else "Student"
                greeting_instruction = f"""
                NEW CALLER JOINED!
                User ID: '{user_id}'
                Name: '{caller_name}'

                Greet {caller_name} warmly in NATIVE TELUGU SCRIPT (తెలుగు లిపి) as EduVoice, their AI learning tutor.
                Example: "నమస్తే {caller_name}! నేను ఎడ్యువాయిస్, మీ AI ట్యూటర్. ఈరోజు ఏం సబ్జెక్ట్ ఆర్ టాపిక్ నేర్చుకుందాం?"
                Keep greeting friendly, welcoming, and under 30 words.
                """

            await session.generate_reply(instructions=greeting_instruction)
    finally:
        # Record final call outcome and duration in call_logs
        record_call_end(call_id=call_id)


if __name__ == "__main__":
    cli.run_app(server)
