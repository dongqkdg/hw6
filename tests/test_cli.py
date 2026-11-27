"""The command-line planner can run without network or an API key."""

from datetime import datetime, timedelta, timezone

from app.cli import run_cli


def test_cli_collects_input_and_prints_weekly_plan():
    now = datetime(2026, 11, 23, 9, tzinfo=timezone(timedelta(hours=9)))
    answers = iter(["월 09:00-10:00", "매일 23:00-07:00", "보고서|60|월 12:00|2", ""])
    output = []

    run_cli(now, None, input_fn=lambda prompt: next(answers), output_fn=output.append)

    printed = "\n".join(output)
    assert "보고서" in printed
    assert "2026-11-23 10:00" in printed
    assert "미배치" in printed
