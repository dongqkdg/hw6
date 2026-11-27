#!/usr/bin/env bash
set -euo pipefail

new_image=${1:?image name required}
expected_sha=${2:?commit SHA required}
container_name=factchat-planner
health_url=http://127.0.0.1:8080/health
retries=${HEALTH_RETRIES:-10}
delay=${HEALTH_DELAY_SECONDS:-2}

previous_image=$(docker container inspect --format '{{.Image}}' "$container_name" 2>/dev/null || true)
previous_sha=""
if [[ -n "$previous_image" ]]; then
  previous_sha=$(docker image inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$previous_image" 2>/dev/null | sed -n 's/^APP_COMMIT_SHA=//p' | head -n 1 || true)
fi

run_container() {
  docker run -d \
    --name "$container_name" \
    --restart unless-stopped \
    -p 127.0.0.1:8080:8080 \
    --env FACTCHAT_API_KEY \
    --env FACTCHAT_BASE_URL \
    --env FACTCHAT_MODEL \
    "$1" >/dev/null
}

healthy() {
  local expected_commit=$1
  for ((attempt=1; attempt<=retries; attempt++)); do
    local response
    if response=$(curl --fail --silent --show-error "$health_url" 2>/dev/null); then
      if python3 -c 'import json, sys; value = json.loads(sys.argv[1]); expected = sys.argv[2]; sys.exit(0 if value.get("status") == "ok" and (not expected or value.get("commit") == expected) else 1)' "$response" "$expected_commit" >/dev/null 2>&1; then
        return 0
      fi
    fi
    sleep "$delay"
  done
  return 1
}

docker rm -f "$container_name" >/dev/null 2>&1 || true
if run_container "$new_image" && healthy "$expected_sha"; then
  echo "Deployment healthy"
  exit 0
fi

echo "Deployment health check failed; restoring previous image" >&2
docker rm -f "$container_name" >/dev/null 2>&1 || true
if [[ -n "$previous_image" ]]; then
  if run_container "$previous_image"; then
    if healthy "$previous_sha"; then
      echo "Previous image restored and healthy" >&2
    else
      echo "Previous image health check failed after rollback" >&2
    fi
  else
    echo "Previous image could not be restored" >&2
  fi
else
  echo "No previous image is available" >&2
fi
exit 1
