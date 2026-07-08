import json
import os

CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"sources": []}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def add_source(name, path):
    config = load_config()
    config["sources"][name] = path
    save_config(config)
    print(f"Added source: {name} -> {path}")

def remove_source(name):
    config = load_config()
    if name in config["sources"]:
        path = config["sources"].pop(name)
        save_config(config)
        print(f"Removed source: {name} ({path})")
    else:
        print(f"Source name not found: {name}")
    
def get_sources():
    config = load_config()
    return config.get("sources", {})