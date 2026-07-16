import json
import os
import subprocess
from pathlib import Path
from paths import CONFIG_FILE, LOG_DIR, WEB_DIR, CADDYFILE_PATH, LMS_HOME, FAIL2BAN_JAIL_PATH, SYSTEMD_SERVICE_PATH

def load_config():
    if not CONFIG_FILE.exists():
        return {"sources": {}}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def generate_caddyfile():
    config = load_config()
    sources = config.get("sources", {})
    username = config.get("username")
    caddy_hash = config.get("password_hash")
    
    lines = [
        ":80 {",
        "    log {",
        f"        output file {LOG_DIR}/access.log {{",
        "            roll_size 10mb",
        "            roll_keep 5",
        "            roll_keep_for 720h",
        "        }",
        "    }",
        "",
        "    # Block all write/delete operations (only allow GET and HEAD)",
        "    @write_ops not method GET HEAD",
        '    respond @write_ops "Method Not Allowed" 405',
        ""
    ]
    
    # Basic auth if configured
    if username and caddy_hash:
        lines.extend([
            "    # Basic Auth",
            "    basic_auth {",
            f"        {username} {caddy_hash}",
            "    }",
            ""
        ])
        
    # Serve configured media sources
    for source_name, source_path in sources.items():
        lines.extend([
            f"    # Serve source: {source_name}",
            f"    handle_path /media/{source_name}/* {{",
            f"        root * {source_path}",
            "        file_server",
            "    }",
            ""
        ])
        
    lines.extend([
        "    # Serve web frontend",
        f"    root * {WEB_DIR}",
        "    file_server",
        "}"
    ])
    
    with open(CADDYFILE_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")
    
    try:
        subprocess.run(["caddy", "fmt", "--overwrite", str(CADDYFILE_PATH)], check=True, capture_output=True)
    except Exception as e:
        print(f"Warning: Could not format Caddyfile: {e}")
    
    print(f"Regenerated Caddyfile at {CADDYFILE_PATH}")
    generate_fail2ban_config(interactive=False)

def generate_fail2ban_config(interactive=True):
    lines = [
        "[caddy-auth]",
        "enabled = true",
        "port    = http,https",
        "filter  = caddy-auth",
        f"logpath = {LOG_DIR}/access.log",
        "maxretry = 5",
        "bantime  = 3600",
        "findtime = 600"
    ]
    with open(FAIL2BAN_JAIL_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Regenerated fail2ban jail config at {FAIL2BAN_JAIL_PATH}")
    
    # Also ensure filter exists (it's mostly static but good to have in LMS_HOME)
    filter_path = LMS_HOME / "fail2ban_caddy_filter.conf"
    if not filter_path.exists():
        filter_content = [
            "[Definition]",
            "failregex = ^.*\"remote_ip\":\"<HOST>\".*\"status\":401.*$",
            "datepattern = \"ts\":(?P<timestamp>\\d+\\.\\d+)",
            "ignoreregex ="
        ]
        with open(filter_path, "w") as f:
            f.write("\n".join(filter_content) + "\n")
    
    if interactive:
        choice = input("\nWould you like to install Fail2ban configs to /etc/fail2ban? (requires sudo) [y/N]: ").strip().lower()
        if choice == 'y':
            try:
                subprocess.run(["sudo", "ln", "-sf", str(FAIL2BAN_JAIL_PATH), "/etc/fail2ban/jail.d/lms.conf"], check=True)
                subprocess.run(["sudo", "ln", "-sf", str(filter_path), "/etc/fail2ban/filter.d/caddy-auth.conf"], check=True)
                subprocess.run(["sudo", "systemctl", "restart", "fail2ban"], check=True)
                print("[OK] Fail2ban configurations installed and service restarted.")
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Failed to install Fail2ban configs: {e}")

def generate_systemd_unit():
    lines = [
        "[Unit]",
        "Description=LMS (Library/Media Server) - Caddy Web Gateway",
        "After=network.target",
        "",
        "[Service]",
        "Type=simple",
        # Use EnvironmentFile if it exists, otherwise fallback to direct env var
        "EnvironmentFile=-/etc/lms.env",
        f"Environment=\"LMS_HOME={LMS_HOME}\"",
        f"WorkingDirectory={LMS_HOME}",
        f"ExecStart=/usr/bin/caddy run --config {CADDYFILE_PATH} --adapter caddyfile",
        "Restart=always",
        "RestartSec=10",
        "User=lms",
        "Group=lms",
        "",
        "# Security Hardening",
        "NoNewPrivileges=true",
        "PrivateTmp=true",
        "ProtectSystem=full",
        "ProtectHome=read-only",
        f"BindPaths={LMS_HOME}",
        "",
        "[Install]",
        "WantedBy=multi-user.target"
    ]
    with open(SYSTEMD_SERVICE_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Generated systemd unit file at {SYSTEMD_SERVICE_PATH}")
    
    choice = input("\nWould you like to install the systemd service? (requires sudo) [y/N]: ").strip().lower()
    if choice == 'y':
        try:
            subprocess.run(["sudo", "ln", "-sf", str(SYSTEMD_SERVICE_PATH), "/etc/systemd/system/lms.service"], check=True)
            subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
            subprocess.run(["sudo", "systemctl", "enable", "--now", "lms"], check=True)
            print("[OK] Systemd service installed, enabled, and started.")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to install systemd service: {e}")

def print_status():
    config = load_config()
    sources = config.get("sources", {})
    username = config.get("username")
    
    print("--- LMS System Status ---")
    print(f"LMS_HOME: {LMS_HOME}")
    print(f"Config File: {CONFIG_FILE} ({'Exists' if CONFIG_FILE.exists() else 'Missing'})")
    print(f"Web Directory: {WEB_DIR}")
    print(f"Log Directory: {LOG_DIR}")
    print(f"Caddyfile: {CADDYFILE_PATH} ({'Exists' if CADDYFILE_PATH.exists() else 'Missing'})")
    
    print("\nMedia Sources:")
    if not sources:
        print("  (No sources configured)")
    for name, path in sources.items():
        exists = os.path.exists(path)
        print(f"  - {name}: {path} ({'Exists' if exists else 'NOT FOUND'})")
        
    print(f"\nAuthentication: {'Configured (User: ' + username + ')' if username else 'Disabled'}")
    
    jail_exists = FAIL2BAN_JAIL_PATH.exists()
    print(f"Fail2ban Jail: {FAIL2BAN_JAIL_PATH} ({'Exists' if jail_exists else 'Missing'})")
    
    svc_exists = SYSTEMD_SERVICE_PATH.exists()
    print(f"Systemd Service: {SYSTEMD_SERVICE_PATH} ({'Exists' if svc_exists else 'Missing'})")

def run_command_with_sudo_fallback(cmd, error_msg_prefix):
    """Runs a command, and if it fails with 'Operation not permitted', asks to retry with sudo."""
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        if "Operation not permitted" in e.stderr:
            print(f"\n[PERMISSION] {error_msg_prefix}: {e.stderr.strip()}")
            choice = input("Would you like to retry this operation with sudo? [y/N]: ").strip().lower()
            if choice == 'y':
                try:
                    subprocess.run(["sudo"] + cmd, check=True)
                    return True
                except subprocess.CalledProcessError as sudo_e:
                    print(f"[ERROR] Sudo operation failed: {sudo_e}")
        else:
            print(f"[ERROR] {error_msg_prefix}: {e.stderr.strip()}")
    return False

def apply_acl(path):
    path = Path(path).resolve()
    print(f"Applying ACL permissions for 'lms' user to: {path}")

    # 1. Apply traverse permission to parent directories
    for parent in reversed(list(path.parents)):
        if parent == Path('/'):
            continue
        
        cmd = ["setfacl", "-m", "u:lms:x", str(parent)]
        if not run_command_with_sudo_fallback(cmd, f"Failed to set traverse ACL on parent '{parent}'"):
            print(f"[WARN] Skipping ACL for {parent}")

    # 2. Apply permissions recursively to current files and directories
    # Apply rx and default rx to source directory itself first
    try:
        cmd1 = ["setfacl", "-m", "u:lms:rx", str(path)]
        cmd2 = ["setfacl", "-d", "-m", "u:lms:rx", str(path)]
        run_command_with_sudo_fallback(cmd1, f"Failed to set rx ACL on source root '{path}'")
        run_command_with_sudo_fallback(cmd2, f"Failed to set default rx ACL on source root '{path}'")
    except Exception as e:
        print(f"[ERROR] Unexpected error applying root ACLs: {e}")
        return

    for root, dirs, files in os.walk(path):
        root_path = Path(root)
        for d in dirs:
            dir_path = root_path / d
            cmd1 = ["setfacl", "-m", "u:lms:rx", str(dir_path)]
            cmd2 = ["setfacl", "-d", "-m", "u:lms:rx", str(dir_path)]
            run_command_with_sudo_fallback(cmd1, f"Failed to set ACL on subdirectory '{dir_path}'")
            run_command_with_sudo_fallback(cmd2, f"Failed to set default ACL on subdirectory '{dir_path}'")
                
        for f in files:
            file_path = root_path / f
            cmd = ["setfacl", "-m", "u:lms:r", str(file_path)]
            run_command_with_sudo_fallback(cmd, f"Failed to set ACL on file '{file_path}'")
                
    print("[ACL] ACL application process completed.")

def remove_acl(path):
    path = Path(path).resolve()
    if not path.exists():
        print(f"[ACL] Path does not exist, skipping ACL removal: {path}")
        return

    print(f"Removing 'lms' ACL permissions from: {path}")

    def remove_single_path_acl(p):
        p_str = str(p)
        try:
            subprocess.run(["setfacl", "-x", "u:lms", p_str], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError:
            pass

        if p.is_dir():
            try:
                subprocess.run(["setfacl", "-d", "-x", "u:lms", p_str], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError:
                pass

    for root, dirs, files in os.walk(path, topdown=False):
        root_path = Path(root)
        for f in files:
            remove_single_path_acl(root_path / f)
        for d in dirs:
            remove_single_path_acl(root_path / d)

    remove_single_path_acl(path)
    print("[ACL] ACL removal completed successfully.")

def add_source(name, path):
    path_obj = Path(path).resolve()
    if not path_obj.exists() or not path_obj.is_dir():
        print(f"Error: Path does not exist or is not a directory: {path}")
        return

    apply_acl(path_obj)

    config = load_config()
    if "sources" not in config:
        config["sources"] = {}
        
    config["sources"][name] = str(path_obj)
    save_config(config)
    print(f"Added source: {name} -> {path_obj}")
    generate_caddyfile()

def remove_source(name):
    config = load_config()
    if "sources" in config and name in config["sources"]:
        path = config["sources"].pop(name)
        save_config(config)
        print(f"Removed source: {name} ({path})")
        remove_acl(path)
        generate_caddyfile()
    else:
        print(f"Source name not found: {name}")
    
def get_sources():
    config = load_config()
    return config.get("sources", {})

def set_password(username, password):
    try:
        result = subprocess.run(
            ["caddy", "hash-password", "--plaintext", password],
            capture_output=True,
            text=True,
            check=True
        )
        caddy_hash = result.stdout.strip()
    except Exception as e:
        print(f"Error generating Caddy password hash: {e}")
        return

    config = load_config()
    config["username"] = username
    config["password_hash"] = caddy_hash
    save_config(config)
    print(f"Password set successfully for user '{username}'.")
    generate_caddyfile()

def remove_password():
    config = load_config()
    username = config.pop("username", None)
    config.pop("password_hash", None)
    save_config(config)
    if username:
        print(f"Password removed for user '{username}'.")
    else:
        print("No password was configured.")
    generate_caddyfile()
