from pathlib import Path

import pytest
from livekit.agents import AgentSession, inference, llm

from agent import Assistant
from db import (
    get_escalations,
    init_db,
    sanitize_summary,
    save_escalation,
    update_escalation_status,
)
from escalation import generate_ref_id


def _llm() -> llm.LLM:
    return inference.LLM(model="openai/gpt-4.1-mini")


# ── Unit tests for DB and Escalation logic ───────────────────────────────────

def test_generate_ref_id():
    ref_id = generate_ref_id()
    assert ref_id.startswith("ESC-")
    assert len(ref_id) == 8


def test_sanitize_summary():
    text = "My password is mysecret123 and my OTP code is 4921. Card number 4532-1111-2222-3333."
    clean = sanitize_summary(text)
    assert "mysecret123" not in clean
    assert "4921" not in clean
    assert "4532-1111-2222-3333" not in clean
    assert "[REDACTED]" in clean or "[REDACTED_CODE]" in clean or "[REDACTED_CARD]" in clean


def test_db_escalation_lifecycle(tmp_path: Path):
    test_db = tmp_path / "test_escalations.db"
    init_db(db_path=test_db)

    # 1. Save escalation
    ref_id = generate_ref_id()
    saved = save_escalation(
        ref_id=ref_id,
        user_id="student_test",
        student_name="Ramesh",
        reason="learner_frustrated",
        issue_summary="Student is confused by quadratic equations, password is 12345",
        context_checked="Explained quadratic formula twice",
        urgency="high",
        language="Tenglish",
        follow_up_method="Teacher Callback",
        db_path=test_db,
    )
    assert saved["ref_id"] == ref_id
    assert saved["status"] == "open"
    assert "12345" not in saved["issue_summary"]  # PII scrubbed

    # 2. Get escalations
    all_tickets = get_escalations(db_path=test_db)
    assert len(all_tickets) == 1
    assert all_tickets[0]["ref_id"] == ref_id

    # 3. Update status
    updated = update_escalation_status(ref_id=ref_id, status="resolved", db_path=test_db)
    assert updated is True

    resolved_tickets = get_escalations(status="resolved", db_path=test_db)
    assert len(resolved_tickets) == 1
    assert resolved_tickets[0]["ref_id"] == ref_id


# ── LiveKit LLM Judged Evaluation Tests ──────────────────────────────────────

@pytest.mark.asyncio
async def test_normal_conversation_no_escalation() -> None:
    """Normal math question should NOT trigger escalation or consent prompt."""
    async with (
        _llm() as llm_engine,
        AgentSession(llm=llm_engine) as session,
    ):
        await session.start(Assistant())
        result = await session.run(user_input="What is 5 plus 5?")

        await (
            result.expect.next_event()
            .is_message(role="assistant")
            .judge(
                llm_engine,
                intent="Answers the math question correctly without creating or offering a human escalation ticket.",
            )
        )
        result.expect.no_more_events()


@pytest.mark.asyncio
async def test_escalation_path_with_consent() -> None:
    """Student asking for human teacher should trigger consent request and create escalation ticket upon agreement."""
    async with (
        _llm() as llm_engine,
        AgentSession(llm=llm_engine) as session,
    ):
        await session.start(Assistant())

        # Step 1: Student expresses severe frustration & asks for human teacher
        result1 = await session.run(
            user_input="I am super frustrated and confused! Can I please talk to a real human teacher?"
        )

        # Agent should ask for permission before creating ticket
        await (
            result1.expect.next_event()
            .is_message(role="assistant")
            .judge(
                llm_engine,
                intent="Asks the student for permission to send their details/topic to a human teacher for a callback.",
            )
        )

        # Step 2: Student consents
        result2 = await session.run(user_input="Yes, please create a ticket for a teacher to call me.")

        # Agent calls create_escalation tool and speaks confirmation with reference ID
        result2.expect.next_event().is_function_call(name="create_escalation")
        result2.expect.next_event().is_function_call_output()
        await (
            result2.expect.next_event()
            .is_message(role="assistant")
            .judge(
                llm_engine,
                intent="Confirms that a support request/ticket has been created, provides a reference ID (like ESC-XXXX), and explains next steps.",
            )
        )


@pytest.mark.asyncio
async def test_escalation_path_consent_denied() -> None:
    """If student says NO to sending details, agent must NOT create ticket."""
    async with (
        _llm() as llm_engine,
        AgentSession(llm=llm_engine) as session,
    ):
        await session.start(Assistant())

        # Step 1: Student asks for teacher
        await session.run(
            user_input="This concept is too hard! I want a real human teacher."
        )

        # Step 2: Student denies consent
        result2 = await session.run(user_input="No, don't send my details to anyone.")

        # Agent should respect decision and NOT create ticket
        await (
            result2.expect.next_event()
            .is_message(role="assistant")
            .judge(
                llm_engine,
                intent="Respects the student's decision, does not create an escalation ticket, and continues helping politely.",
            )
        )
