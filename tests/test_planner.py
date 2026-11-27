"""DB와 네트워크 없이 실행하는 일정 배치 규칙 테스트."""

from datetime import datetime, timedelta, timezone
from importlib import import_module

import pytest


KST = timezone(timedelta(hours=9))
DAY = datetime(2026, 11, 27, 9, tzinfo=KST)


def at(hour, minute=0):
    return DAY.replace(hour=hour, minute=minute)


def task(task_id, minutes, deadline, priority=1):
    return {
        "id": task_id,
        "duration_minutes": minutes,
        "deadline": deadline,
        "priority": priority,
    }


@pytest.fixture
def planner():
    return import_module("app.planner")


def test_overlapping_busy_intervals_are_merged(planner):
    assert planner.free_slots(
        (at(9), at(13)), [(at(10), at(11)), (at(10, 30), at(12))]
    ) == [(at(9), at(10)), (at(12), at(13))]


def test_busy_time_is_never_scheduled(planner):
    result = planner.schedule_tasks(
        at(9), [(at(9), at(10))], [task("write", 60, at(12))]
    )
    assert result["scheduled"] == [
        {"task_id": "write", "start": at(10), "end": at(11)}
    ]


def test_time_before_now_is_never_scheduled(planner):
    result = planner.schedule_tasks(
        at(10), [], [task("write", 60, at(12))]
    )
    assert result["scheduled"][0]["start"] >= at(10)


def test_impossible_deadline_is_reported_as_unscheduled(planner):
    result = planner.schedule_tasks(
        at(9), [(at(9), at(10))], [task("write", 60, at(10))]
    )
    assert result["scheduled"] == []
    assert result["unscheduled"] == [
        {"task_id": "write", "reason": "no_available_slot"}
    ]


def test_short_slot_does_not_split_a_task(planner):
    result = planner.schedule_tasks(
        at(9), [(at(9, 30), at(10))], [task("write", 60, at(10, 30))]
    )
    assert result["scheduled"] == []
    assert result["unscheduled"] == [
        {"task_id": "write", "reason": "no_available_slot"}
    ]


def test_scheduled_tasks_do_not_overlap(planner):
    result = planner.schedule_tasks(
        at(9), [], [task("a", 60, at(12)), task("b", 60, at(12))]
    )
    first, second = result["scheduled"]
    assert first["end"] <= second["start"]


def test_shorter_task_can_fill_gap_before_higher_priority_task(planner):
    result = planner.schedule_tasks(
        at(9),
        [(at(9, 30), at(10))],
        [task("long", 60, at(11), 2), task("short", 30, at(11), 1)],
    )
    by_id = {item["task_id"]: item for item in result["scheduled"]}
    assert by_id["long"]["start"] == at(10)
    assert by_id["short"]["start"] == at(9)
    assert result["unscheduled"] == []


def test_earlier_deadline_is_scheduled_first(planner):
    result = planner.schedule_tasks(
        at(9), [], [task("later", 60, at(12)), task("sooner", 60, at(11))]
    )
    assert [item["task_id"] for item in result["scheduled"]] == ["sooner", "later"]


def test_higher_priority_breaks_deadline_tie(planner):
    result = planner.schedule_tasks(
        at(9), [], [task("low", 60, at(12), 1), task("high", 60, at(12), 2)]
    )
    assert [item["task_id"] for item in result["scheduled"]] == ["high", "low"]


def test_identical_input_produces_identical_schedule(planner):
    tasks = [task("b", 30, at(12)), task("a", 30, at(12))]
    first = planner.schedule_tasks(at(9), [], tasks)
    assert planner.schedule_tasks(at(9), [], tasks) == first


@pytest.mark.parametrize(
    "invalid_busy",
    [[(at(10), at(10))], [(at(11), at(10))]],
)
def test_invalid_busy_interval_is_rejected(planner, invalid_busy):
    with pytest.raises(ValueError):
        planner.schedule_tasks(at(9), invalid_busy, [task("write", 30, at(12))])
