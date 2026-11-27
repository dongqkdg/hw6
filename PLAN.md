# HW6 implementation plan

## Product

A weekly planner that schedules tasks into open time, ordered by deadline and priority. ChatKHU can turn free-form input into structured busy periods, sleep periods, and tasks.

## Testable rules

1. A task must fit entirely inside a free interval.
2. Busy and sleep intervals are never scheduled over.
3. Past time is not offered as a candidate interval.
4. Earlier deadlines are scheduled first; ties use higher priority.
5. Invalid or overlapping input is rejected or counted, never silently treated as valid.
6. An LLM item is used only after schema and time validation.
7. Invalid JSON is retried once; unavailable or failing LLM calls use rule-based input.
8. The health endpoint reports the deployed commit.
9. Local deployment checks health and restores the previous image if the new container fails.
10. CI tests run before image build and deployment.

## LLM contract and fallback

The LLM extracts structured planner input. Its HTTP post function is injectable so tests use a fake and stay offline. JSON decode errors are retried once. Missing settings, missing key, failed calls, or invalid response data fall back to the rule-based parser; invalid items are counted. API credentials are read only from `FACTCHAT_API_KEY`.

## Delivery sequence

The existing history pairs tests and implementation commits. CI/CD tests run on GitHub-hosted runners; build and deploy depend on the test job. A deliberate failing test was pushed as a CI-gate demonstration and captured in `ci-failure.png`; it is removed in the submission fix so the final branch has a passing suite.
