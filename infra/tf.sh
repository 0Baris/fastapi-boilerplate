#!/usr/bin/env bash
#
# Terraform wrapper. Loads infra/.env (exporting every TF_VAR_* and the
# TF_STATE_* backend settings), then runs terraform against envs/prod.
#
#   ./tf.sh init
#   ./tf.sh plan
#   ./tf.sh apply
#   ./tf.sh output
#
# On `init`, the GCS backend bucket + prefix are injected from
# TF_STATE_BUCKET / TF_STATE_PREFIX via -backend-config so no
# environment-specific values live in the .tf files.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "error: $ENV_FILE not found." >&2
  echo "Copy .env.example to .env and fill in your values first." >&2
  exit 1
fi

# Export everything defined in .env for the duration of this process.
set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

PROD_DIR="$SCRIPT_DIR/envs/prod"

if [ "${1:-}" = "init" ]; then
  : "${TF_STATE_BUCKET:?TF_STATE_BUCKET must be set in .env}"
  : "${TF_STATE_PREFIX:?TF_STATE_PREFIX must be set in .env}"
  shift
  exec terraform -chdir="$PROD_DIR" init \
    -backend-config="bucket=$TF_STATE_BUCKET" \
    -backend-config="prefix=$TF_STATE_PREFIX" \
    "$@"
fi

exec terraform -chdir="$PROD_DIR" "$@"
