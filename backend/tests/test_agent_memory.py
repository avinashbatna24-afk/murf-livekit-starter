import tempfile
from pathlib import Path

import pytest
from livekit.agents import AgentSession, inference, llm

from agent import Assistant
from db import get_user_memory, init_db, save_user_memory


def _llm() -> llm.LLM:
    return inference.LLM(model="google/gemini-2.5-flash")


@pytest.fixture
def temp_db_env(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "agent_test_memory.db"
        init_db(db_path)
        # Patch db_path in db module
        monkeypatch.setattr("db.DB_PATH", db_path)
        yield db_path


@pytest.mark.asyncio
async def test_consent_required_before_saving(temp_db_env) -> None:
    """Test that agent asks for consent before saving facts and respects refusal."""
    async with (
        _llm() as llm_inst,
        AgentSession(llm=llm_inst) as session,
    ):
        await session.start(Assistant())

        # User shares facts but says NOT to save
        result = await session.run(
            user_input="My name is Ramesh and I am in Class 10 studying Quadratic Equations. Please do NOT save my info."
        )

        # Evaluate agent response: must respect decision and not claim to have saved
        await (
            result.expect.next_event()
            .is_message(role="assistant")
            .judge(
                llm_inst,
                intent="""
                Acknowledges the user's input or answers about Quadratic Equations,
                and confirms or respects that their data will NOT be saved.
                Does NOT insist on saving data after user said no.
                """,
            )
        )

        # Verify DB is empty for user
        assert get_user_memory("ramesh", db_path=temp_db_env) is None


@pytest.mark.asyncio
async def test_explicit_consent_triggers_save(temp_db_env) -> None:
    """Test that explicit consent triggers save_user_memory tool execution."""
    async with (
        _llm() as llm_inst,
        AgentSession(llm=llm_inst) as session,
    ):
        await session.start(Assistant())

        # User gives explicit consent to save
        result = await session.run(
            user_input="I am Ramesh, Class 10 Math. Yes, please save my learning progress for next time!"
        )

        # Verify tool call was invoked or response acknowledges saving
        event = result.expect.next_event()
        if event.type == "function_call":
            assert event.function_call.name == "save_user_memory"
        else:
            await event.is_message(role="assistant").judge(
                llm_inst,
                intent="Acknowledges saving or asking details to save Ramesh's progress.",
            )


@pytest.mark.asyncio
async def test_forget_me_request(temp_db_env) -> None:
    """Test that 'forget me' request deletes caller record."""
    # Pre-seed memory for Ramesh
    save_user_memory(
        user_id="ramesh",
        name="Ramesh",
        facts={
            "current_level": "Class 10 Math",
            "topics_covered": ["Quadratic Equations"],
        },
        db_path=temp_db_env,
    )
    assert get_user_memory("ramesh", db_path=temp_db_env) is not None

    async with (
        _llm() as llm_inst,
        AgentSession(llm=llm_inst) as session,
    ):
        await session.start(Assistant())

        result = await session.run(
            user_input="My user_id is ramesh. Please forget me and wipe all my saved data."
        )

        event = result.expect.next_event()
        if event.type == "function_call":
            assert event.function_call.name == "forget_user_memory"

        # Verify database record was wiped
        assert get_user_memory("ramesh", db_path=temp_db_env) is None
