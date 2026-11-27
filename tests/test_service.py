"""The service uses injected fake HTTP responses; no network is contacted."""

import json
from datetime import datetime, timedelta, timezone

from app.service import build_week_plan
from app.llm import LLMClient


KST = timezone(timedelta(hours=9))
NOW = datetime(2026, 11, 23, 9, tzinfo=KST)  # Monday
BUSY = "월 09:00-10:00"
SLEEP = "매일 23:00-07:00"
TASKS = "보고서|60|월 12:00|2"


def reply(content):
    return {"choices": [{"message": {"content": content}}]}


def valid_payload():
    return {
        "busy": [{"start": "2026-11-23T09:00:00+09:00", "end": "2026-11-23T10:00:00+09:00"}],
        "sleep": {"start": "23:00", "end": "07:00"},
        "tasks": [{"id": "보고서", "duration_minutes": 60, "deadline": "2026-11-23T12:00:00+09:00", "priority": 2}],
    }


def test_non_json_response_is_retried_exactly_once(monkeypatch):
    monkeypatch.setenv("FACTCHAT_API_KEY", "fake-test-key")
    calls = []
    responses = [reply("not json"), reply(json.dumps(valid_payload()))]

    def fake_post(url, *, headers, json, timeout):
        calls.append(url)
        return responses.pop(0)

    client = LLMClient(fake_post, base_url="https://example.invalid/v1", model="test-model")
    result = build_week_plan(NOW, BUSY, SLEEP, TASKS, client)
    assert len(calls) == 2
    assert result["source"] == "llm"
    assert result["scheduled"][0]["start"] == NOW.replace(hour=10)


def test_non_json_twice_uses_rule_based_fallback(monkeypatch):
    monkeypatch.setenv("FACTCHAT_API_KEY", "fake-test-key")
    calls = []

    def fake_post(url, *, headers, json, timeout):
        calls.append(url)
        return reply("not json")

    client = LLMClient(fake_post, base_url="https://example.invalid/v1", model="test-model")
    result = build_week_plan(NOW, BUSY, SLEEP, TASKS, client)
    assert len(calls) == 2
    assert result["source"] == "rules"
    assert result["scheduled"][0]["start"] == NOW.replace(hour=10)


def test_invalid_llm_items_are_discarded_and_counted(monkeypatch):
    monkeypatch.setenv("FACTCHAT_API_KEY", "fake-test-key")
    payload = valid_payload()
    payload["busy"].append({"start": "invalid", "end": "2026-11-23T11:00:00+09:00"})
    payload["tasks"].append({"id": "bad", "duration_minutes": -20, "deadline": "2026-11-23T12:00:00+09:00", "priority": 1})

    def fake_post(url, *, headers, json, timeout):
        return reply(__import__("json").dumps(payload))

    client = LLMClient(fake_post, base_url="https://example.invalid/v1", model="test-model")
    result = build_week_plan(NOW, BUSY, SLEEP, TASKS, client)
    assert result["source"] == "llm"
    assert result["rejected_count"] == 2
    assert [item["task_id"] for item in result["scheduled"]] == ["보고서"]


def test_missing_key_uses_rules_without_calling_post(monkeypatch):
    monkeypatch.delenv("FACTCHAT_API_KEY", raising=False)

    def forbidden_post(*args, **kwargs):
        raise AssertionError("post must not be called")

    client = LLMClient(forbidden_post, base_url="https://example.invalid/v1", model="test-model")
    result = build_week_plan(NOW, BUSY, SLEEP, TASKS, client)
    assert result["source"] == "rules"
    assert result["scheduled"][0]["start"] == NOW.replace(hour=10)


def test_call_failure_uses_rules(monkeypatch):
    monkeypatch.setenv("FACTCHAT_API_KEY", "fake-test-key")

    def failed_post(*args, **kwargs):
        raise RuntimeError("request failed")

    client = LLMClient(failed_post, base_url="https://example.invalid/v1", model="test-model")
    result = build_week_plan(NOW, BUSY, SLEEP, TASKS, client)
    assert result["source"] == "rules"
    assert result["scheduled"][0]["start"] == NOW.replace(hour=10)


def test_sleep_and_busy_time_are_kept_free_of_tasks_without_llm(monkeypatch):
    monkeypatch.delenv("FACTCHAT_API_KEY", raising=False)
    result = build_week_plan(
        NOW,
        "월 09:00-10:00",
        "매일 10:00-11:00",
        "보고서|60|월 13:00|2",
        None,
    )
    assert result["scheduled"][0]["start"] == NOW.replace(hour=11)


def test_rule_fallback_reports_unparseable_input(monkeypatch):
    monkeypatch.delenv("FACTCHAT_API_KEY", raising=False)
    result = build_week_plan(NOW, "???", SLEEP, "??", None)
    assert result["source"] == "rules"
    assert result["rejected_count"] == 2
    assert result["scheduled"] == []
