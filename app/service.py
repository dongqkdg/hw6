"""Turn weekly input into a validated, deterministic plan."""

import re
from datetime import datetime, time, timedelta

from app.planner import schedule_tasks
from app.quiz import validate_payload


WEEKDAYS = {day: index for index, day in enumerate("월화수목금토일")}
BUSY_PATTERN = re.compile(r"([월화수목금토일])\s+(\d\d:\d\d)-(\d\d:\d\d)")
TASK_PATTERN = re.compile(r"([^|]+)\|(\d+)\|([월화수목금토일])\s+(\d\d:\d\d)\|([1-5])")
SLEEP_PATTERN = re.compile(r"매일\s+(\d\d:\d\d)-(\d\d:\d\d)")


def _day_time(week_start, day, clock):
    return datetime.combine(
        (week_start + timedelta(days=WEEKDAYS[day])).date(),
        time.fromisoformat(clock),
        tzinfo=week_start.tzinfo,
    )


def _rule_input(busy_text, sleep_text, tasks_text, week_start):
    busy = []
    tasks = []
    rejected = 0
    for part in re.split(r"[,\n]+", busy_text):
        if not part.strip():
            continue
        match = BUSY_PATTERN.fullmatch(part.strip())
        try:
            if match is None:
                raise ValueError("invalid busy input")
            day, start_text, end_text = match.groups()
            start = _day_time(week_start, day, start_text)
            end = _day_time(week_start, day, end_text)
            if start >= end:
                raise ValueError("invalid busy interval")
            busy.append((start, end))
        except ValueError:
            rejected += 1

    for part in tasks_text.splitlines():
        if not part.strip():
            continue
        match = TASK_PATTERN.fullmatch(part.strip())
        try:
            if match is None:
                raise ValueError("invalid task input")
            task_id, duration, day, deadline_text, priority = match.groups()
            if not task_id.strip() or int(duration) <= 0:
                raise ValueError("invalid task")
            tasks.append({"id": task_id.strip(), "duration_minutes": int(duration), "deadline": _day_time(week_start, day, deadline_text), "priority": int(priority)})
        except ValueError:
            rejected += 1

    sleep = None
    match = SLEEP_PATTERN.fullmatch(sleep_text.strip())
    try:
        if match is None:
            raise ValueError("invalid sleep input")
        start, end = (time.fromisoformat(value) for value in match.groups())
        if start == end:
            raise ValueError("invalid sleep interval")
        sleep = (start, end)
    except ValueError:
        rejected += 1
    return {"busy": busy, "sleep": sleep, "tasks": tasks, "rejected_count": rejected}


def _sleep_intervals(week_start, week_end, sleep):
    if sleep is None:
        return []
    start_time, end_time = sleep
    intervals = []
    for offset in range(-1, 7):
        day = (week_start + timedelta(days=offset)).date()
        start = datetime.combine(day, start_time, tzinfo=week_start.tzinfo)
        end = datetime.combine(day, end_time, tzinfo=week_start.tzinfo)
        if end <= start:
            end += timedelta(days=1)
        start, end = max(start, week_start), min(end, week_end)
        if start < end:
            intervals.append((start, end))
    return intervals


def build_week_plan(now, busy_text, sleep_text, tasks_text, client=None):
    """Build this week's schedule; fall back to strict local input syntax."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must include timezone")
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)
    source = "rules"
    data = None
    validation_failure = 0
    if client is not None:
        try:
            raw = client.extract(busy_text, sleep_text, tasks_text, week_start, week_end)
        except Exception:
            # External calls and untrusted responses must not stop local planning.
            pass
        else:
            try:
                data = validate_payload(raw, week_start, week_end)
                source = "llm"
            except Exception:
                validation_failure = 1
    if data is None:
        data = _rule_input(busy_text, sleep_text, tasks_text, week_start)
    busy = data["busy"] + _sleep_intervals(week_start, week_end, data["sleep"])
    result = schedule_tasks(now, busy, data["tasks"])
    metrics = {
        "llm_calls": getattr(client, "calls", 0),
        "llm_failures": getattr(client, "failures", 0) + validation_failure,
        "discarded_items": data["rejected_count"],
        "fallbacks": int(source == "rules"),
    }
    return {**result, "source": source, "rejected_count": data["rejected_count"], "metrics": metrics, "week_start": week_start, "week_end": week_end}
