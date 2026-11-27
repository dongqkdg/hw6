# 이번 주 플래너

바쁜 시간, 매일 수면 시간, 이번 주 할 일을 입력하면 빈 시간에 연속으로 할 일을 배치합니다. 마감이 빠른 일부터 배치하고, 마감이 같으면 우선순위가 높은 일을 먼저 배치합니다. 배치할 수 없는 일은 별도로 표시합니다.

## 실행

```bash
python -m app --base-url CHATKHU_OPENAI_COMPATIBLE_V1_URL --model CHATKHU_MODEL_NAME
```

ChatKHU API 키는 실행 환경의 `FACTCHAT_API_KEY`에 설정합니다. `--base-url`은 `/v1`까지의 기본 URL이며 프로그램이 `/chat/completions`를 붙입니다. `FACTCHAT_BASE_URL`과 `FACTCHAT_MODEL` 환경 변수로 두 인자를 대신할 수도 있습니다. 주소 또는 모델이 없거나 키가 없으면 아래의 규칙 기반 입력으로 계속 실행합니다.

입력 예시:

```text
바쁜 시간: 월 09:00-10:00, 화 14:00-15:00
수면 시간: 매일 23:00-07:00
할 일: 보고서|60|월 12:00|2
할 일: 발표 준비|90|금 18:00|3
할 일: (빈 줄로 종료)
```

할 일의 숫자는 예상 소요 시간(분)과 우선순위(1~5)입니다. 바쁜 시간과 할 일은 이번 주의 요일을 사용합니다. 수면 시간은 매일 반복되며 자정을 넘길 수 있습니다. LLM이 사용 가능하면 입력을 JSON으로 구조화하되, `app/quiz.py`에서 검증한 항목만 일정 계산에 사용합니다. JSON이 아니면 한 번만 재시도합니다. 호출에 실패하면 규칙 기반 형식으로 입력을 읽으며, 읽을 수 없는 항목은 개수로 표시합니다.

출력 마지막 줄에는 이번 실행의 LLM 호출 횟수, 실패 횟수, 버린 항목 수, 규칙 기반 대체 횟수를 표시합니다. 키가 없어 LLM 호출을 시도하지 않은 경우 호출과 실패는 0회이며 대체 동작은 1회입니다.

테스트는 `python -m pytest -q`로 실행합니다. 테스트의 HTTP 호출은 모두 주입한 가짜 `post` 함수를 사용합니다.

## 로컬 컨테이너와 GitHub Actions

컨테이너는 8080번 포트에서 `GET /health`와 `POST /plan`을 제공합니다. `/health`는 상태와 이미지에 넣은 커밋 해시를 반환합니다. `/plan`에는 현재 시각을 시간대가 포함된 ISO 형식으로 전달합니다.

```bash
docker build --build-arg APP_COMMIT_SHA=$(git rev-parse HEAD) -t factchat-planner:local .
docker run -d --name factchat-planner -p 127.0.0.1:8080:8080 \
  --env FACTCHAT_API_KEY --env FACTCHAT_BASE_URL --env FACTCHAT_MODEL \
  factchat-planner:local
curl --fail http://127.0.0.1:8080/health
```

`POST /plan` 요청 본문 예시:

```json
{
  "now": "2026-11-23T09:00:00+09:00",
  "busy": "월 09:00-10:00",
  "sleep": "매일 23:00-07:00",
  "tasks": "보고서|60|월 12:00|2"
}
```

GitHub 저장소의 **Settings → Actions → Runners**에서 이 컴퓨터를 self-hosted runner로 등록하고, Docker 엔진을 실행한 상태로 둡니다. 테스트는 GitHub 호스팅 러너에서 실행하고, 이미지 빌드와 배포는 이 로컬 러너에서 실행합니다. 저장소 Secret `FACTCHAT_API_KEY`와 Variables `FACTCHAT_BASE_URL`, `FACTCHAT_MODEL`을 설정합니다. `main`에 push하면 `test → build → deploy` 순서로 실행됩니다. pull request에서는 `test`만 실행됩니다. 배포는 로컬 Docker 컨테이너를 교체하고 `/health`를 확인하며, 새 컨테이너가 정상 응답하지 않으면 직전 이미지로 되돌립니다. 처음 배포할 때는 되돌릴 이미지가 없으므로 실패 상태로 종료합니다.
