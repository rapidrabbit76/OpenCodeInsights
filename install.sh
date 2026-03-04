#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${HOME}/.local/share/opencode-insights"
COMMAND_DIR="${HOME}/.config/opencode/command"
REPO_URL="https://github.com/rapidrabbit76/OpenCodeInsights.git"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
DIM='\033[2m'
RESET='\033[0m'

info()  { echo -e "${GREEN}✓${RESET} $1"; }
warn()  { echo -e "${RED}✗${RESET} $1"; }
dim()   { echo -e "${DIM}  $1${RESET}"; }

echo ""
echo "OpenCodeInsights Installer"
echo "=========================="
echo ""

# 1. Check python3
if ! command -v python3 &>/dev/null; then
  warn "python3 not found. Install Python 3.10+ first."
  exit 1
fi
info "python3 found: $(python3 --version 2>&1)"

# 2. Check OpenCode DB
DB_PATH="${HOME}/.local/share/opencode/opencode.db"
if [ -f "$DB_PATH" ]; then
  info "OpenCode DB found"
else
  warn "OpenCode DB not found at ${DB_PATH}"
  dim "Run some OpenCode sessions first, then re-run this installer."
  exit 1
fi

# 3. Clone or update
if [ -d "$INSTALL_DIR/.git" ]; then
  info "Updating existing installation..."
  git -C "$INSTALL_DIR" pull --quiet
  info "Updated to latest"
else
  if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
  fi
  info "Cloning to ${INSTALL_DIR}..."
  git clone --quiet "$REPO_URL" "$INSTALL_DIR"
  info "Cloned"
fi

# 4. Create output directory
mkdir -p "${INSTALL_DIR}/output"
info "Output directory ready"

# 5. Register OpenCode command
mkdir -p "$COMMAND_DIR"
sed "s|{{INSIGHTS_HOME}}|${INSTALL_DIR}|g" "${INSTALL_DIR}/insights.md" > "${COMMAND_DIR}/insights.md"
info "Registered /insights command (paths resolved)"

# 6. Set environment variable in shell rc
ENV_LINE="export OPENCODE_INSIGHTS_HOME=\"${INSTALL_DIR}\""
SHELL_RC=""

if [ -f "${HOME}/.zshrc" ]; then
  SHELL_RC="${HOME}/.zshrc"
elif [ -f "${HOME}/.bashrc" ]; then
  SHELL_RC="${HOME}/.bashrc"
fi

if [ -n "$SHELL_RC" ]; then
  if grep -q "OPENCODE_INSIGHTS_HOME" "$SHELL_RC" 2>/dev/null; then
    info "Environment variable already set in $(basename "$SHELL_RC")"
  else
    echo "" >> "$SHELL_RC"
    echo "# OpenCodeInsights" >> "$SHELL_RC"
    echo "$ENV_LINE" >> "$SHELL_RC"
    info "Added OPENCODE_INSIGHTS_HOME to $(basename "$SHELL_RC")"
  fi
else
  warn "No .zshrc or .bashrc found. Add manually:"
  dim "${ENV_LINE}"
fi

echo ""
echo "=========================="
info "Done! Open a new OpenCode session and run: /insights"
echo ""
