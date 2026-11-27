#!/usr/bin/env bash
set -euo pipefail

new_image=${1:?image name required}
container_name=factchat-planner
health_url=http://127.0.0.1:8080/health
retries=${HEALTH_RETRIES:-10}
delay=${HEALTH_DELAY_SECONDS:-2}

previous_image=$(docker container inspect --format '{{.Image}}' "$container_name" 2>/dev/null || true)

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
  for ((attempt=1; attempt<=retries; attempt++)); do
    if curl --fail --silent --show-error "$health_url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$delay"
  done
  return 1
}

docker rm -f "$container_name" >/dev/null 2>&1 || true
if run_container "$new_image" && healthy; then
  echo "Deployment healthy"
  exit 0
fi

echo "Deployment health check failed; restoring previous image" >&2
docker rm -f "$container_name" >/dev/null 2>&1 || true
if [[ -n "$previous_image" ]]; then
  if run_container "$previous_image"; then
    echo "Previous image restored" >&2
  else
    echo "Previous image could not be restored" >&2
  fi
else
  echo "No previous image is available" >&2
fi
exit 1
