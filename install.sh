#!/usr/bin/env bash

# ==============================================================================
# LMS (Lime's Media Server) - Professional Linux Installer
# ==============================================================================
# 
# This script installs LMS to the current user's home directory.
#
# GOALS:
# 1.  Maintain security via a restricted system service user ('lms').
# 2.  Maintain ownership of application code by the installing user.
# 3.  Ensure persistent data (configs, logs, cache) survives updates.
# 4.  Automate system integration (Systemd, Caddy, ACLs, global CLI).
# 5.  Support multiple distributions (Debian, Ubuntu, Arch, Fedora).
#
# DESIGN NOTES:
# - LMS_HOME: Root of the installation (~/.lms).
# - VIRTUAL ENV: Python dependencies are isolated in ~/.lms/venv.
# - SYSTEMD: Caddy is the primary runtime, running as the 'lms' user.
# - ACLs: Bridge the gap between the installing user (owner) and 'lms' (reader).
# ==============================================================================

# Enable strict error handling
# -e: Exit immediately if a command fails
# -u: Treat unset variables as an error
# -o pipefail: Ensure pipe failures are caught
set -euo pipefail

# --- Configuration & Constants ---
APP_NAME="lms"
REPO_URL="https://github.com/EmilPtr/LMS.git"
REPO_BRANCH="prod"
INSTALL_USER=$(whoami)
# Resolve home directory reliably
INSTALL_USER_HOME=$(getent passwd "$INSTALL_USER" | cut -d: -f6)
LMS_HOME="$INSTALL_USER_HOME/.lms"
ENV_FILE="/etc/lms.env"
SERVICE_FILE="/etc/systemd/system/lms.service"
SERVICE_USER="lms"
BIN_LINK="/usr/local/bin/lms"

# Colors for professional console output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# --- Helper Functions ---

log() { echo -e "${BLUE}${BOLD}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}${BOLD}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}${BOLD}[WARN]${NC} $1"; }
error() { echo -e "${RED}${BOLD}[ERROR]${NC} $1" >&2; exit 1; }

# Dependency check: Ensure basic tools are present before we start
check_prerequisites() {
    log "Checking prerequisites..."
    if ! command -v git &>/dev/null; then
        warn "Git is not installed. Will attempt to install via package manager."
    fi
}

# Root check: Ensure we can elevate to sudo, but aren't running AS root
check_user_context() {
    if [[ $EUID -eq 0 && ${SUDO_USER:-} == "" ]]; then
        error "Do not run this script directly as root. Run it as the user who will own the installation."
    fi
    
    log "Checking sudo access..."
    if ! sudo -v &>/dev/null; then
        error "This script requires sudo privileges to install system components."
    fi
}

# OS Detection: Determine package manager and specific requirements
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS_ID=$ID
    else
        error "Could not detect operating system (missing /etc/os-release)."
    fi
    log "Operating System detected: $OS_ID"
}

# Install system-level dependencies based on detected OS
install_dependencies() {
    log "Updating system and installing dependencies..."
    case "$OS_ID" in
        debian|ubuntu)
            sudo apt-get update -qq
            sudo apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https curl python3 python3-venv git acl ffmpeg fail2ban
            
            # Caddy Official Repository Installation (Debian/Ubuntu)
            if ! command -v caddy &>/dev/null; then
                log "Adding Caddy official repository..."
                curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
                curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
                sudo apt-get update -qq
                sudo apt-get install -y -qq caddy
            fi
            ;;
        arch)
            sudo pacman -Syu --noconfirm --needed python python-virtualenv git caddy acl ffmpeg fail2ban
            ;;
        fedora|rhel)
            sudo dnf install -y python3 python3-virtualenv git acl ffmpeg fail2ban
            if ! command -v caddy &>/dev/null; then
                log "Enabling Caddy COPR repository..."
                sudo dnf install -y 'dnf-command(copr)'
                sudo dnf copr enable -y @caddy/caddy
                sudo dnf install -y caddy
            fi
            ;;
        *)
            warn "Unsupported distribution '$OS_ID'. Ensure python3, venv, git, caddy, acl, and ffmpeg are installed manually."
            ;;
    esac

    # Hard verification of critical dependencies
    local required_tools=("git" "python3" "caddy" "setfacl")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &>/dev/null; then
            error "Required dependency '$tool' is missing. The installer cannot continue. Please install it and try again."
        fi
    done
}

# Create a restricted system user to run the server
create_service_user() {
    if id "$SERVICE_USER" &>/dev/null; then
        log "Service user '$SERVICE_USER' already exists."
    else
        log "Creating restricted system service user '$SERVICE_USER'..."
        # -r: system account
        # -s /usr/sbin/nologin: prevent shell login
        # -M: do not create home directory
        sudo useradd -r -s /usr/sbin/nologin -M "$SERVICE_USER"
    fi
}

# Clone or update the source code in LMS_HOME
setup_lms_home() {
    log "Preparing installation directory at $LMS_HOME..."
    if [[ ! -d "$LMS_HOME" ]]; then
        mkdir -p "$LMS_HOME"
    fi

    if [[ -d "$LMS_HOME/.git" ]]; then
        log "LMS repository already exists. Fetching latest updates (branch: $REPO_BRANCH)..."
        cd "$LMS_HOME"
        git fetch origin "$REPO_BRANCH"
        git reset --hard "origin/$REPO_BRANCH"
    else
        log "Cloning LMS repository from $REPO_URL (branch: $REPO_BRANCH)..."
        git clone --branch "$REPO_BRANCH" --single-branch "$REPO_URL" "$LMS_HOME"
    fi

    # Ownership: The installing user owns the files
    sudo chown -R "$INSTALL_USER":"$INSTALL_USER" "$LMS_HOME"
}

# Setup the Python virtual environment and install requirements
setup_venv() {
    log "Configuring Python virtual environment..."
    cd "$LMS_HOME"
    
    # Create venv if missing
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
    fi
    
    # Identify the best requirements file
    REQ_FILE="requirements.txt"
    if [[ -f "requirements-lock.txt" ]]; then
        REQ_FILE="requirements-lock.txt"
    fi

    log "Installing dependencies into venv using $REQ_FILE..."
    ./venv/bin/pip install --upgrade pip -q
    if [[ -f "$REQ_FILE" ]]; then
        ./venv/bin/pip install -r "$REQ_FILE" -q
    else
        warn "No requirements file found in repository. Installing defaults (moviepy, mutagen)..."
        ./venv/bin/pip install moviepy mutagen -q
    fi
}

# Setup global environment and CLI shortcut
configure_environment() {
    log "Setting up global environment file at $ENV_FILE..."
    # This file is used by Systemd and potentially other shell environments
    echo "LMS_HOME=$LMS_HOME" | sudo tee "$ENV_FILE" > /dev/null

    log "Creating global 'lms' command at $BIN_LINK..."
    # This wrapper ensures LMS_HOME is always set correctly for the CLI
    cat <<EOF | sudo tee "$BIN_LINK" > /dev/null
#!/usr/bin/env bash
export LMS_HOME="$LMS_HOME"
exec "$LMS_HOME/venv/bin/python" "$LMS_HOME/main.py" "\$@"
EOF
    sudo chmod +x "$BIN_LINK"
}

# Apply precise ACLs to grant the 'lms' user necessary access
apply_permissions() {
    log "Configuring filesystem ACLs for service user '$SERVICE_USER'..."
    
    # Ensure mandatory state directories exist
    mkdir -p "$LMS_HOME/log" "$LMS_HOME/cache"
    
    # 1. Grant 'lms' user traversal (x) access to the user's home directory.
    # Without this, Caddy cannot reach ~/.lms/web even with inner permissions.
    sudo setfacl -m u:"$SERVICE_USER":x "$INSTALL_USER_HOME" || warn "Could not set ACL on $INSTALL_USER_HOME. If the service fails to start, ensure $SERVICE_USER can traverse to $LMS_HOME."

    # 2. Grant 'lms' user read/traversal (rx) access to the entire LMS_HOME.
    # This allows Caddy to serve static assets from /web.
    sudo setfacl -R -m u:"$SERVICE_USER":rx "$LMS_HOME"
    
    # 3. Grant 'lms' user full access (rwx) to log and cache directories.
    # Caddy needs to write access logs and Python needs cache access.
    sudo setfacl -R -m u:"$SERVICE_USER":rwx "$LMS_HOME/log"
    sudo setfacl -R -m u:"$SERVICE_USER":rwx "$LMS_HOME/cache"
    
    # 4. Set Default ACLs so new files in these directories inherit the same permissions.
    sudo setfacl -dR -m u:"$SERVICE_USER":rwx "$LMS_HOME/log"
    sudo setfacl -dR -m u:"$SERVICE_USER":rwx "$LMS_HOME/cache"
}

# Create and enable the systemd service unit using internal CLI logic for consistency
setup_systemd() {
    log "Leveraging LMS CLI for systemd integration..."
    
    # We must set LMS_HOME for the CLI to function correctly
    export LMS_HOME="$LMS_HOME"
    
    # Generate the unit file (lms.service) inside LMS_HOME using config.py's internal logic.
    # config.py now includes EnvironmentFile support and hardening options.
    # We pass 'n' to the interactive prompt to prevent it from installing automatically
    # as we want to control the link and startup ourselves in this script.
    "$LMS_HOME/venv/bin/python" "$LMS_HOME/main.py" config setup-systemd <<EOF
n
EOF

    # Install the generated service file to the system
    log "Linking and enabling the service..."
    sudo ln -sf "$LMS_HOME/lms.service" "$SERVICE_FILE"
    
    sudo systemctl daemon-reload
    sudo systemctl enable lms.service > /dev/null
    
    # Final check: Does a Caddyfile exist? If not, initialization is required.
    if [[ ! -f "$LMS_HOME/Caddyfile" ]]; then
        warn "No Caddyfile found. You must run 'lms init' to finalize setup."
    else
        log "Existing configuration detected. You can start the service now."
    fi
}

# Integrate Fail2ban if installed
setup_fail2ban() {
    if command -v fail2ban-client &>/dev/null; then
        log "Integrating Fail2ban via LMS CLI..."
        export LMS_HOME="$LMS_HOME"
        "$LMS_HOME/venv/bin/python" "$LMS_HOME/main.py" config setup-fail2ban <<EOF
n
EOF
    else
        warn "Fail2ban not found. Skipping security integration."
    fi
}

# --- Main Logic Flow ---

main() {
    echo -e "${BLUE}${BOLD}================================================================${NC}"
    echo -e "${BLUE}${BOLD}              LMS (Lime's Media Server) Installer              ${NC}"
    echo -e "${BLUE}${BOLD}================================================================${NC}"

    check_prerequisites
    check_user_context
    detect_os
    install_dependencies
    create_service_user
    setup_lms_home
    setup_venv
    configure_environment
    apply_permissions
    setup_systemd
    setup_fail2ban

    echo -e "\n${GREEN}${BOLD}================================================================${NC}"
    echo -e "${GREEN}${BOLD}                    Installation Successful!                    ${NC}"
    echo -e "${GREEN}${BOLD}================================================================${NC}"
    echo -e "Location:   $LMS_HOME"
    echo -e "Service:    lms.service (User: $SERVICE_USER)"
    echo -e "Command:    lms (Available globally)"
    echo -e ""
    echo -e "${BOLD}INITIALIZATION STEPS:${NC}"
    echo -e "1. Run ${BLUE}lms init${NC} to create your admin user and media source."
    echo -e "   This will also generate your first Caddyfile."
    echo -e ""
    echo -e "2. Start the server:"
    echo -e "   ${BLUE}sudo systemctl start lms${NC}"
    echo -e ""
    echo -e "3. Monitor progress:"
    echo -e "   ${BLUE}lms config info${NC}"
    echo -e "================================================================\n"
}

# Run the installer
main
