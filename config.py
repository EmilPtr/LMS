import json
import os
import subprocess

CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
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
    
    workspace_dir = os.path.abspath(os.path.dirname(__file__))
    web_dir = os.path.join(workspace_dir, "web")
    
    lines = [
        ":80 {",
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
        
    lines.extend([
        "    # Serve manifest.json",
        f"    handle /manifest.json {{",
        f"        root * {workspace_dir}",
        "        file_server",
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
        f"    root * {web_dir}",
        "    file_server",
        "}"
    ])
    
    caddyfile_path = os.path.join(workspace_dir, "Caddyfile")
    with open(caddyfile_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Regenerated Caddyfile at {caddyfile_path}")

def apply_acl(path):
    """
    Applies read-only ACL permissions for the 'lms' user to the source directory.
    - Parents: ensures execute (x) permission on all parent directories leading to the source.
    - Source: recursively applies read-execute (rx) to directories and read (r) to files.
    - Future files: configures default (d:) ACLs so future files inherit read (r) and directories inherit read-execute (rx).
    """
    if not os.path.isabs(path):
        path = os.path.abspath(path)
        
    print(f"Applying ACL permissions for 'lms' user to: {path}")

    # 1. Apply traverse permission to parent directories
    parents = []
    current = os.path.dirname(path)
    while current and current != '/':
        parents.append(current)
        current = os.path.dirname(current)
    parents.reverse()
    
    for parent in parents:
        try:
            subprocess.run(["setfacl", "-m", "u:lms:x", parent], check=True, capture_output=True, text=True)
            print(f"[ACL] Set traverse (x) permission on parent: {parent}")
        except subprocess.CalledProcessError as e:
            print(f"[ACL WARN] Failed to set traverse ACL on parent '{parent}': {e.stderr.strip()}")

    # 2. Apply permissions recursively to current files and directories
    # Apply rx and default rx to source directory itself first
    try:
        subprocess.run(["setfacl", "-m", "u:lms:rx", path], check=True, capture_output=True, text=True)
        subprocess.run(["setfacl", "-d", "-m", "u:lms:rx", path], check=True, capture_output=True, text=True)
        print(f"[ACL] Set rx and default rx on source root: {path}")
    except subprocess.CalledProcessError as e:
        print(f"[ACL ERROR] Failed to set ACL on source root '{path}': {e.stderr.strip()}")
        return

    # Now recursively walk and apply
    for root, dirs, files in os.walk(path):
        for d in dirs:
            dir_path = os.path.join(root, d)
            try:
                subprocess.run(["setfacl", "-m", "u:lms:rx", dir_path], check=True, capture_output=True, text=True)
                subprocess.run(["setfacl", "-d", "-m", "u:lms:rx", dir_path], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                print(f"[ACL WARN] Failed to set ACL on subdirectory '{dir_path}': {e.stderr.strip()}")
                
        for f in files:
            file_path = os.path.join(root, f)
            try:
                subprocess.run(["setfacl", "-m", "u:lms:r", file_path], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                print(f"[ACL WARN] Failed to set ACL on file '{file_path}': {e.stderr.strip()}")
                
    print("[ACL] ACL application completed successfully.")

def remove_acl(path):
    """
    Removes all regular and default ACL permissions for the 'lms' user from the source directory.
    """
    if not os.path.isabs(path):
        path = os.path.abspath(path)

    if not os.path.exists(path):
        print(f"[ACL] Path does not exist, skipping ACL removal: {path}")
        return

    print(f"Removing 'lms' ACL permissions from: {path}")

    # Helper to remove ACL for a single file/directory
    def remove_single_path_acl(p):
        # Remove regular ACL
        try:
            subprocess.run(["setfacl", "-x", "u:lms", p], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            # Silently ignore if no such ACL entry or file moved/removed during walk
            pass

        # Remove default ACL if it's a directory
        if os.path.isdir(p):
            try:
                subprocess.run(["setfacl", "-d", "-x", "u:lms", p], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                pass

    # Walk recursively and remove from bottom up to avoid issues
    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            remove_single_path_acl(os.path.join(root, f))
        for d in dirs:
            remove_single_path_acl(os.path.join(root, d))

    # Remove from root itself
    remove_single_path_acl(path)
    print("[ACL] ACL removal completed successfully.")

def add_source(name, path):
    if not os.path.exists(path) or not os.path.isdir(path):
        print(f"Error: Path does not exist or is not a directory: {path}")
        return

    path = os.path.abspath(path)
    apply_acl(path)

    config = load_config()
    if "sources" not in config:
        config["sources"] = {}
        
    config["sources"][name] = path
    save_config(config)
    print(f"Added source: {name} -> {path}")
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