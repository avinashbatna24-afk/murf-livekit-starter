import json
import sys
from pathlib import Path

# Add src dir to sys.path so imports work smoothly
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from db import get_analytics_summary  # noqa: E402

db_arg = sys.argv[1] if len(sys.argv) > 1 else None
db_path = Path(db_arg) if db_arg else None

try:
    summary = get_analytics_summary(db_path)
    print(json.dumps(summary))
except Exception as e:
    # Print empty default JSON structure if database error occurs
    print(
        json.dumps(
            {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "success_rate": 0.0,
                "avg_duration_seconds": 0,
                "failure_breakdown": {},
                "channel_breakdown": {},
                "recent_calls": [],
                "error": str(e),
            }
        )
    )
