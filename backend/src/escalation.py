"""
escalation.py — Day 7 Human Escalation Helper Module for EduVoice

Provides:
  1. generate_ref_id: Generates a unique reference ID (e.g. ESC-4821) for human help tickets.
  2. dispatch_webhook: Sends a formatted notification to a Discord or generic HTTP webhook
     when an escalation request is created.
"""

import logging
import os
import random
from typing import Any

import httpx

logger = logging.getLogger("agent.escalation")


def generate_ref_id() -> str:
    """Generate a unique human readable reference ID (e.g. ESC-4821)."""
    num = random.randint(1000, 9999)
    return f"ESC-{num}"


async def dispatch_webhook(escalation_data: dict[str, Any]) -> bool:
    """
    Send an escalation payload to Discord or HTTP Webhook if configured in environment.
    Supported env vars: DISCORD_WEBHOOK_URL, HUMAN_HELP_WEBHOOK_URL, WEBHOOK_URL.
    """
    webhook_url = (
        os.environ.get("DISCORD_WEBHOOK_URL")
        or os.environ.get("HUMAN_HELP_WEBHOOK_URL")
        or os.environ.get("WEBHOOK_URL")
    )
    if not webhook_url:
        logger.info("No webhook URL configured; skipping external webhook dispatch.")
        return False

    ref_id = escalation_data.get("ref_id", "ESC-0000")
    name = escalation_data.get("student_name", "Student")
    reason = escalation_data.get("reason", "Teacher assistance requested")
    urgency = escalation_data.get("urgency", "medium").upper()
    summary = escalation_data.get("issue_summary", "")
    context = escalation_data.get("context_checked", "")
    method = escalation_data.get("follow_up_method", "Teacher Callback")
    lang = escalation_data.get("language", "Tenglish")

    # If it's a Discord webhook, format as a rich embed
    if "discord.com/api/webhooks" in webhook_url:
        color = 0xFF4500 if urgency in ["HIGH", "EMERGENCY"] else 0xF97316
        payload = {
            "username": "EduVoice Teacher Desk",
            "avatar_url": "https://murf.ai/favicon.ico",
            "embeds": [
                {
                    "title": f"🚨 Human Escalation Request: {ref_id}",
                    "description": f"**Student:** {name}\n**Reason:** {reason}\n**Urgency:** `{urgency}`",
                    "color": color,
                    "fields": [
                        {"name": "Issue Summary", "value": summary or "None", "inline": False},
                        {"name": "Context / Topics", "value": context or "None", "inline": False},
                        {"name": "Language & Preferred Contact", "value": f"{lang} | {method}", "inline": True},
                    ],
                    "footer": {"text": "EduVoice #VoiceForBharat — Day 7 Human Escalation"},
                }
            ],
        }
    else:
        # Standard HTTP webhook payload
        payload = escalation_data

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(webhook_url, json=payload)
            res.raise_for_status()
            logger.info("Successfully dispatched escalation %s to webhook", ref_id)
            return True
    except Exception as exc:
        logger.warning("Failed to dispatch escalation %s to webhook: %s", ref_id, exc)
        return False
