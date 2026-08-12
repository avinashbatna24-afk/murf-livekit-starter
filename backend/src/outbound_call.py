"""
outbound_call.py — EduVoice Daily Practice Reminder (Day 6)

Usage:
    uv run python src/outbound_call.py
    uv run python src/outbound_call.py sip:yourname@sip.linphone.org

How it works:
    1. Creates a LiveKit room for this call
    2. Dispatches the EduVoice agent worker into that room
    3. Dials the student's Linphone SIP URI through the outbound SIP trunk
    4. The student's Linphone app rings — when answered, EduVoice greets them
"""

import asyncio
import logging
import os
import sys
import uuid
from datetime import timedelta

from dotenv import load_dotenv
from livekit import api

load_dotenv(".env.local")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("outbound-caller")

# ── Configuration ──────────────────────────────────────────────────────────────

AGENT_NAME = os.getenv("AGENT_NAME", "my-agent")
SIP_TRUNK_ID = os.getenv("SIP_OUTBOUND_TRUNK_ID", "")
TARGET_SIP = os.getenv("LINPHONE_TARGET_SIP", "")   # e.g. sip:abiba@sip.linphone.org

# Timeout (seconds) before we treat "no answer" and hang up
NO_ANSWER_TIMEOUT = 40


# ── Outcome helpers ────────────────────────────────────────────────────────────

async def delete_room(lk: api.LiveKitAPI, room_name: str) -> None:
    """Clean up the room after the call ends or on error."""
    try:
        await lk.room.delete_room(api.DeleteRoomRequest(room=room_name))
        logger.info("Room '%s' deleted.", room_name)
    except Exception as exc:
        logger.warning("Could not delete room '%s': %s", room_name, exc)


# ── Main dial function ─────────────────────────────────────────────────────────

async def make_outbound_call(target_sip: str) -> None:
    """
    Dial target_sip (a Linphone SIP URI) and connect the EduVoice agent.

    Handles:
      - No answer  -> times out after NO_ANSWER_TIMEOUT seconds
      - Busy / SIP error -> logs and cleans up room
      - Successful call  -> agent runs until student or agent hangs up
    """
    if not SIP_TRUNK_ID:
        logger.error(
            "SIP_OUTBOUND_TRUNK_ID is not set in .env.local.\n"
            "Follow the Linphone SIP trunk setup steps in README.md first."
        )
        return

    if not target_sip:
        logger.error(
            "No target SIP URI provided.\n"
            "Set LINPHONE_TARGET_SIP in .env.local or pass the SIP URI as an argument:\n"
            "  uv run python src/outbound_call.py sip:yourname@sip.linphone.org"
        )
        return

    room_name = f"outbound-{uuid.uuid4().hex[:8]}"

    # LiveKit SIP expects just the username, not a full URI like sip:user@domain
    # Strip "sip:" prefix and "@domain" suffix if present
    sip_user = target_sip
    if sip_user.startswith("sip:"):
        sip_user = sip_user[4:]
    if "@" in sip_user:
        sip_user = sip_user.split("@")[0]

    logger.info("Starting outbound call -> %s (sip_user=%s, room: %s)", target_sip, sip_user, room_name)

    async with api.LiveKitAPI(
        url=os.getenv("LIVEKIT_URL"),
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET"),
    ) as lk:

        # Step 1 -- Dispatch EduVoice agent into the room
        # The metadata carries the call context so the agent can open properly.
        try:
            dispatch = await lk.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name=AGENT_NAME,
                    room=room_name,
                    metadata=f"outbound:{target_sip}",
                )
            )
            # Different livekit-api versions use different field names
            did = (
                getattr(dispatch, "dispatch_id", None)
                or getattr(dispatch, "id", None)
                or str(dispatch)
            )
            logger.info("Agent dispatched (dispatch_id=%s)", did)
        except Exception as exc:
            logger.error("Failed to dispatch agent: %s", exc)
            return

        # Step 2 -- Dial the student via Linphone SIP trunk
        try:
            logger.info("Dialing %s via LiveKit SIP trunk (waiting for answer)...", sip_user)
            sip_participant = await lk.sip.create_sip_participant(
                api.CreateSIPParticipantRequest(
                    sip_trunk_id=SIP_TRUNK_ID,
                    sip_call_to=sip_user,
                    room_name=room_name,
                    participant_identity="sip-student",
                    participant_name="Student",
                    wait_until_answered=True,               # Wait until call is physically picked up
                    ringing_timeout=timedelta(seconds=40),  # Ring for up to 40 seconds
                )
            )
            logger.info(
                "Student ANSWERED! SIP participant connected (sip_call_id=%s).",
                sip_participant.sip_call_id,
            )
        except Exception as exc:
            logger.error(
                "SIP call failed or declined: %s (type: %s)",
                exc, type(exc).__name__,
            )
            await delete_room(lk, room_name)
            return

        # Step 3 -- Wait for the call to finish (student or agent hangs up)
        logger.info("Call connected and in progress. Waiting for hangup...")
        await _wait_for_call_end(lk, room_name)
        logger.info("Call ended normally.")


async def _wait_for_call_end(lk: api.LiveKitAPI, room_name: str) -> None:
    """Poll until the SIP participant leaves the room (call ended)."""
    while True:
        await asyncio.sleep(2)
        try:
            participants = await lk.room.list_participants(
                api.ListParticipantsRequest(room=room_name)
            )
            sip_connected = any(
                p.identity == "sip-student"
                for p in participants.participants
            )
            if not sip_connected:
                logger.info("SIP participant disconnected -- call ended.")
                return
        except Exception:
            # Room deleted by agent hang_up tool or API
            return


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Allow passing the SIP URI as a CLI argument, otherwise use env variable
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_SIP
    asyncio.run(make_outbound_call(target))
