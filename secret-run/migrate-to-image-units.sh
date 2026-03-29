#!/usr/bin/env bash
# ABOUTME: One-time migration script to switch from user-local secret-run
# and systemd units to the image-shipped versions in /usr/local/bin and
# /usr/lib/systemd/user. Run this after rebasing to the image version that
# includes secret-run in overlay-root.

set -euo pipefail

echo "Disabling old user-local timer..."
systemctl --user disable laptop-backup.timer

echo "Removing old unit files..."
rm -f ~/.config/systemd/user/laptop-backup.service
rm -f ~/.config/systemd/user/laptop-backup.timer

echo "Removing old symlinks..."
rm -f ~/.local/bin/secret-run
rm -f ~/.local/bin/laptop-backup

echo "Reloading systemd user daemon..."
systemctl --user daemon-reload

echo "Enabling image-shipped timer..."
systemctl --user enable --now laptop-backup.timer

echo "Done. Verify with: systemctl --user status laptop-backup.timer"
