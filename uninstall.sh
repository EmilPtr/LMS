#!/usr/bin/env bash

# ==============================================================================
# LMS (Lime's Media Server) - Cleanup / Uninstaller Script
# ==============================================================================
# This script removes LMS components to emulate a fresh install state.
# USE WITH CAUTION: This deletes system files and configuration.
# ==============================================================================

set -euo pipefail

# --- Configuration ---
INSTALL_USER=$(whoami)
INSTALL_USER_HOME=$(getent passwd "$INSTALL_USER" | cut -d: -f6)
LMS_HOME="$INSTALL_USER_HOME/.lms"
ENV_FILE="/etc/lms.env"
SERVICE_FILE="/etc/systemd/system/lms.service"
SERVICE_USER="lms"
BIN_LINK="/usr/local/bin/lms"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

log() { echo -e "[INFO] $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

echo -e "${RED}${BOLD}!!! WARNING !!!${NC}"
echo "This script will delete LMS configuration, services, and the installation directory."
echo "Media files outside of $LMS_HOME will NOT be touched."
read -p "Are you sure you want to proceed? [y/N]: " confirm
if [[ $confirm != [yY] ]]; then
    echo "Aborted."
    exit 0
fi

# 1. Stop and disable the service
if systemctl is-active --quiet lms; then
    log "Stopping lms.service..."
    sudo systemctl stop lms
fi
if [[ -f "$SERVICE_FILE" ]]; then
    log "Disabling and removing lms.service..."
    sudo systemctl disable lms >/dev/null 2>&1 || true
    sudo rm -f "$SERVICE_FILE"
    sudo systemctl daemon-reload
fi

# 2. Remove the global CLI command
if [[ -L "$BIN_LINK" || -f "$BIN_LINK" ]]; then
    log "Removing global 'lms' command..."
    sudo rm -f "$BIN_LINK"
fi

# 3. Remove the environment file
if [[ -f "$ENV_FILE" ]]; then
    log "Removing environment file $ENV_FILE..."
    sudo rm -f "$ENV_FILE"
fi

# 4. Remove the service user
if id "$SERVICE_USER" &>/dev/null; then
    log "Removing service user '$SERVICE_USER'..."
    sudo userdel "$SERVICE_USER" || warn "Could not delete user '$SERVICE_USER'. It might still be in use."
fi

# 5. Clean up ACLs on the home directory
# We only remove the 'lms' user's access
log "Cleaning up ACLs on $INSTALL_USER_HOME..."
sudo setfacl -x u:"$SERVICE_USER" "$INSTALL_USER_HOME" || true

# 6. Delete the installation directory
if [[ -d "$LMS_HOME" ]]; then
    log "Deleting installation directory $LMS_HOME..."
    rm -rf "$LMS_HOME"
fi

success "Cleanup complete. Your system is now in a fresh state for re-installation."
