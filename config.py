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

def add_source(name, path):
    if not os.path.exists(path) or not os.path.isdir(path):
        print(f"Error: Path does not exist or is not a directory: {path}")
        return

    path = os.path.abspath(path)

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