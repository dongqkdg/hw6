"""Validate untrusted LLM planner data before it reaches the scheduler."""

from datetime import datetime, time, timedelta


def _datetime(value, week_start, week_end):
    if not isinstance(value, str):
        raise ValueError("datetime must be text")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("datetime must include timezone")
    if not week_start <= parsed < week_end:
        raise ValueError("datetime outside this week")
    return parsed


def _sleep_time(value):
    if not isinstance(value, str):
        raise ValueError("time must be text")
    parsed = time.fromisoformat(value)
    if parsed.tzinfo is not None or len(value) != 5:
        raise ValueError("time must be HH:MM")
    return parsed


def validate_payload(payload, week_start, week_end):
    """Return valid items and a count of rejected items."""
    if not isinstance(payload, dict):
        raise ValueError("response must be an object")
    if not all(isinstance(payload.get(key), list) for key in ("busy", "tasks")):
        raise ValueError("busy and tasks must be lists")

    busy = []
    tasks = []
    rejected = 0
    for item in payload["busy"]:
        try:
            start = _datetime(item["start"], week_start, week_end)
            end = _datetime(item["end"], week_start, week_end + timedelta(days=1))
            if start >= end or end > week_end:
                raise ValueError("invalid interval")
            busy.append((start, end))
        except (KeyError, TypeError, ValueError):
            rejected += 1

    for item in payload["tasks"]:
        try:
            task_id = item["id"]
            duration = item["duration_minutes"]
            priority = item["priority"]
            deadline = _datetime(item["deadline"], week_start, week_end)
            if not isinstance(task_id, str) or not task_id.strip():
                raise ValueError("invalid task id")
            if type(duration) is not int or duration <= 0:
                raise ValueError("invalid duration")
            if type(priority) is not int or not 1 <= priority <= 5:
                raise ValueError("invalid priority")
            tasks.append({"id": task_id.strip(), "duration_minutes": duration, "deadline": deadline, "priority": priority})
        except (KeyError, TypeError, ValueError):
            rejected += 1

    sleep = None
    try:
        raw_sleep = payload["sleep"]
        start = _sleep_time(raw_sleep["start"])
        end = _sleep_time(raw_sleep["end"])
        if start == end:
            raise ValueError("sleep interval must have length")
        sleep = (start, end)
    except (KeyError, TypeError, ValueError):
        rejected += 1
    return {"busy": busy, "sleep": sleep, "tasks": tasks, "rejected_count": rejected}
