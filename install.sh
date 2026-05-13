#!/bin/sh
# install.sh — Install the latest task-tui release from GitHub
# Usage: curl -fsSL https://raw.githubusercontent.com/lbesnard/task-tui/main/install.sh | sh

set -e

REPO="lbesnard/task-tui"
API_URL="https://api.github.com/repos/${REPO}/releases/latest"

echo "Fetching latest task-tui version..."
VERSION=$(curl -fsSL "$API_URL" | sed -n 's/.*"tag_name": *"v\([^"]*\)".*/\1/p')

if [ -z "$VERSION" ]; then
  echo "Error: could not determine the latest version." >&2
  exit 1
fi

echo "Latest version: ${VERSION}"

WHEEL_URL="https://github.com/${REPO}/releases/download/v${VERSION}/task_tui-${VERSION}-py3-none-any.whl"

if command -v pipx >/dev/null 2>&1; then
  echo "Installing via pipx..."
  pipx install "$WHEEL_URL" --force
elif command -v pip >/dev/null 2>&1; then
  echo "Installing via pip..."
  pip install "$WHEEL_URL" --upgrade
else
  echo "Error: neither pipx nor pip was found. Please install one of them first." >&2
  exit 1
fi

echo "task-tui ${VERSION} installed successfully."
