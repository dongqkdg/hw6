"""Deterministic scheduling without storage or network access."""

from datetime import timedelta


def free_slots(window, busy_intervals):
    """Return free half-open intervals inside ``window``."""
    window_start, window_end = window
    if window_start >= window_end:
        raise ValueError("window start must be before end")

    busy = []
    for start, end in busy_intervals:
        if start >= end:
            raise ValueError("busy interval start must be before end")
        if start < window_end and end > window_start:
            busy.append((max(start, window_start), min(end, window_end)))

    slots = []
    cursor = window_start
    for start, end in sorted(busy):
        if start > cursor:
            slots.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < window_end:
        slots.append((cursor, window_end))
    return slots


def schedule_tasks(now, busy_intervals, tasks):
    """Place tasks when a continuous slot of sufficient length exists."""
    busy = list(busy_intervals)
    for start, end in busy:
        if start >= end:
            raise ValueError("busy interval start must be before end")

    scheduled = []
    unscheduled = []
    cursor = now
    ordered_tasks = sorted(tasks, key=lambda task: (task["deadline"], -task["priority"], str(task["id"])))
    for task in ordered_tasks:
        duration = task["duration_minutes"]
        if duration <= 0:
            raise ValueError("task duration must be positive")
        deadline = task["deadline"]
        placement = None
        if deadline > cursor:
            for start, end in free_slots((cursor, deadline), busy):
                if end - start >= timedelta(minutes=duration):
                    finish = start + timedelta(minutes=duration)
                    placement = {"task_id": task["id"], "start": start, "end": finish}
                    cursor = finish
                    busy.append((placement["start"], finish))
                    scheduled.append(placement)
                    break
        if placement is None:
            unscheduled.append({"task_id": task["id"], "reason": "no_available_slot"})
    return {"scheduled": scheduled, "unscheduled": unscheduled}
