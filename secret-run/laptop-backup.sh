#!/usr/bin/env bash
# ABOUTME: Backup script that runs restic to a local repo, then syncs to S3.
# Uses secret-run to unseal the restic password. AWS credentials come from
# the credential_process configured in ~/.aws/config.

set -euo pipefail

SECRET_RUN="/usr/bin/secret-run"
RESTIC="/home/linuxbrew/.linuxbrew/bin/restic"
AWS="/home/linuxbrew/.linuxbrew/bin/aws"

RESTIC_REPO="${HOME}/backup/restic-repo"
BACKUP_DIRS=("${HOME}/Documents" "${HOME}/Pictures")
S3_BUCKET="s3://sam-lemur-fedora-backup"
AWS_PROFILE="garage-backup"

# --- Restic backup (local) ---

echo "Starting restic backup..."
"${SECRET_RUN}" run --profile restic-backup -- \
    "${RESTIC}" backup \
    --repo "${RESTIC_REPO}" \
    --exclude-caches \
    --exclude '.git' \
    "${BACKUP_DIRS[@]}"

echo "Running restic forget + prune..."
"${SECRET_RUN}" run --profile restic-backup -- \
    "${RESTIC}" forget \
    --repo "${RESTIC_REPO}" \
    --keep-daily 7 \
    --keep-weekly 4 \
    --keep-monthly 6 \
    --prune

# --- Sync to Garage S3 ---

echo "Syncing restic repo to Garage..."
"${AWS}" s3 sync \
    "${RESTIC_REPO}" \
    "${S3_BUCKET}" \
    --profile "${AWS_PROFILE}" \
    --delete

echo "Backup complete."
