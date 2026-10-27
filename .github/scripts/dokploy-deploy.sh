#!/usr/bin/env bash
# Trigger a Dokploy deployment and wait until it finishes.
# Usage: dokploy-deploy.sh <applicationId> <title>
# Env: DOKPLOY_URL (e.g. http://localhost:3000/api), DOKPLOY_API_KEY.
# Fails if the API refuses the call, if the deployment ends in error,
# or if it does not finish within DEPLOY_TIMEOUT seconds (default 600).
set -euo pipefail

app_id="$1"
title="$2"
timeout="${DEPLOY_TIMEOUT:-600}"

api_get() {
  curl -fsS --max-time 30 -H "x-api-key: ${DOKPLOY_API_KEY}" \
    "${DOKPLOY_URL}/application.one?applicationId=${app_id}"
}

deployment_ids() {
  api_get | jq -r '.deployments[].deploymentId' | sort
}

before="$(deployment_ids)"

curl -fsS --max-time 60 -X POST "${DOKPLOY_URL}/application.deploy" \
  -H "x-api-key: ${DOKPLOY_API_KEY}" \
  -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg id "$app_id" --arg t "$title" \
        '{applicationId: $id, title: ("ci " + $t)}')" \
  -o /dev/null -w 'application.deploy HTTP %{http_code}\n'

deadline=$((SECONDS + timeout))
new_id=""
while (( SECONDS < deadline )); do
  sleep 5
  if [[ -z "$new_id" ]]; then
    new_id="$(comm -13 <(echo "$before") <(deployment_ids) | head -n1)"
    [[ -z "$new_id" ]] && continue
    echo "deployment ${new_id} created"
  fi
  status="$(api_get | jq -r --arg d "$new_id" \
    '.deployments[] | select(.deploymentId == $d) | .status')"
  case "$status" in
    done)  echo "deployment ${new_id}: done"; exit 0 ;;
    error) echo "::error::deployment ${new_id} failed in Dokploy"; exit 1 ;;
    *)     echo "deployment ${new_id}: ${status:-pending}" ;;
  esac
done

echo "::error::deployment not finished after ${timeout}s"
exit 1
