"""OpenAI-compatible ChatKHU client with injectable HTTP transport."""

import json as json_module
import os
from urllib.request import Request, urlopen


class MissingAPIKey(Exception):
    pass


def http_post(url, *, headers, json, timeout):
    request = Request(
        url,
        data=json_module.dumps(json, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json_module.load(response)


class LLMClient:
    def __init__(self, post, *, base_url, model):
        self.post = post
        self.base_url = base_url.rstrip("/")
        self.model = model

    def extract(self, busy_text, sleep_text, tasks_text, week_start, week_end):
        key = os.environ.get("FACTCHAT_API_KEY")
        if not key:
            raise MissingAPIKey()
        prompt = (
            "Return only JSON with keys busy, sleep, tasks. "
            "busy is a list of {start,end} ISO datetimes with timezone. "
            "sleep is {start,end} in HH:MM for every day. "
            "tasks is a list of {id,duration_minutes,deadline,priority}; "
            "priority is an integer 1 through 5. Keep only information from the user. "
            f"Week: {week_start.isoformat()} to {week_end.isoformat()}.\n"
            f"Busy: {busy_text}\nSleep: {sleep_text}\nTasks: {tasks_text}"
        )
        for attempt in range(2):
            response = self.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0},
                timeout=15,
            )
            content = response["choices"][0]["message"]["content"]
            try:
                return json_module.loads(content)
            except (TypeError, json_module.JSONDecodeError):
                if attempt == 1:
                    raise ValueError("LLM returned non-JSON twice") from None
