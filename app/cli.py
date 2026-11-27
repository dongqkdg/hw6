"""Interactive weekly planner output."""

from app.service import build_week_plan


def run_cli(now, client, *, input_fn=input, output_fn=print):
    busy = input_fn("이번 주 바쁜 시간 (예: 월 09:00-10:00, 화 14:00-15:00): ")
    sleep = input_fn("매일 수면 시간 (예: 매일 23:00-07:00): ")
    output_fn("할 일을 한 줄씩 입력하세요. 형식: 이름|분|마감 요일 시각|우선순위(1-5). 빈 줄로 종료합니다.")
    task_lines = []
    while True:
        line = input_fn("할 일: ")
        if not line.strip():
            break
        task_lines.append(line)

    result = build_week_plan(now, busy, sleep, "\n".join(task_lines), client)
    output_fn(f"이번 주 플래너 ({result['week_start'].date()} ~ {(result['week_end'].date())})")
    for item in sorted(result["scheduled"], key=lambda entry: entry["start"]):
        output_fn(f"{item['start']:%Y-%m-%d %H:%M} ~ {item['end']:%H:%M}  {item['task_id']}")
    output_fn("미배치")
    for item in result["unscheduled"]:
        output_fn(f"- {item['task_id']}: 배치 가능한 연속 시간이 없습니다")
    output_fn(f"무시한 입력: {result['rejected_count']}개")
    metrics = result["metrics"]
    output_fn(
        f"LLM 호출 {metrics['llm_calls']}회 | 실패 {metrics['llm_failures']}회 | "
        f"버린 항목 {metrics['discarded_items']}개 | 대체 동작 {metrics['fallbacks']}회"
    )
    return result
