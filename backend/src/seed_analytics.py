import sys
from pathlib import Path

src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from db import record_call_end, record_call_start, update_call_progress  # noqa: E402


def seed_sample_calls(db_path: Path | None = None) -> None:
    """Seed initial sample call logs into SQLite database for visual demonstration."""
    sample_calls = [
        {
            "call_id": "call_sample_01",
            "user_id": "ramesh",
            "caller_name": "Ramesh",
            "channel": "Browser",
            "topic": "Photosynthesis",
            "outcome": "successful",
            "ex": 2,
            "esc": False,
            "mem": True,
            "reason": "",
        },
        {
            "call_id": "call_sample_02",
            "user_id": "priya",
            "caller_name": "Priya",
            "channel": "SIP Outbound",
            "topic": "Quadratic Equations",
            "outcome": "successful",
            "ex": 1,
            "esc": False,
            "mem": True,
            "reason": "",
        },
        {
            "call_id": "call_sample_03",
            "user_id": "student_99",
            "caller_name": "Student",
            "channel": "Browser",
            "topic": "General Practice",
            "outcome": "failed",
            "ex": 0,
            "esc": False,
            "mem": False,
            "reason": "Caller disconnected before completing an exercise or topic",
        },
        {
            "call_id": "call_sample_04",
            "user_id": "ramesh",
            "caller_name": "Ramesh",
            "channel": "Browser",
            "topic": "Python loops",
            "outcome": "successful",
            "ex": 1,
            "esc": True,
            "mem": True,
            "reason": "",
        },
        {
            "call_id": "call_sample_05",
            "user_id": "kiran",
            "caller_name": "Kiran",
            "channel": "SIP Outbound",
            "topic": "Newton's Laws",
            "outcome": "failed",
            "ex": 0,
            "esc": False,
            "mem": False,
            "reason": "User declined practice exercise",
        },
    ]

    for item in sample_calls:
        record_call_start(
            call_id=item["call_id"],
            user_id=item["user_id"],
            caller_name=item["caller_name"],
            channel=item["channel"],
            topic_discussed=item["topic"],
            db_path=db_path,
        )
        update_call_progress(
            call_id=item["call_id"],
            exercises_inc=item["ex"],
            escalation_created=item["esc"],
            memory_saved=item["mem"],
            topic_discussed=item["topic"],
            db_path=db_path,
        )
        record_call_end(
            call_id=item["call_id"],
            outcome=item["outcome"],
            failure_reason=item["reason"],
            db_path=db_path,
        )

    print(f"Successfully seeded {len(sample_calls)} call logs into database.")


if __name__ == "__main__":
    seed_sample_calls()
