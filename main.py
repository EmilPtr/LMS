import sys
import paths # Ensure LMS_HOME is checked first
from config import *
from gen_manifest import *

from paths import HELP_FILE_PATH

def print_help():
    if HELP_FILE_PATH.exists():
        with open(HELP_FILE_PATH, 'r') as f:
            print(f.read())
    else:
        print(f"Error: Help file not found at {HELP_FILE_PATH}")

arguments = sys.argv[1:]

if len(arguments) < 1:
    print_help()
    sys.exit(1)

command_name = arguments[0]
subcommand = arguments[1] if len(arguments) > 1 else None


if command_name == "config":
    if subcommand == "add-source":
        if len(arguments) < 4:
            print("Usage: lms config add-source <name> <path>")
        else:
            name = arguments[2]
            path = arguments[3]
            add_source(name, path)
        
    elif subcommand == "remove-source":
        if len(arguments) < 3:
            print("Usage: lms config remove-source <name>")
        else:
            name = arguments[2]
            remove_source(name)

    elif subcommand == "set-password":
        if len(arguments) < 3:
            print("Usage: lms config set-password <password> [username]")
        else:
            password = arguments[2]
            username = arguments[3] if len(arguments) > 3 else "lms"
            set_password(username, password)

    elif subcommand == "remove-password":
        remove_password()

    elif subcommand == "setup-systemd":
        generate_systemd_unit()

    elif subcommand == "setup-fail2ban":
        generate_fail2ban_config()

    elif subcommand == "info":
        print_status()


elif command_name == "help":
    print_help()


elif command_name == "generate":
    manifest = generate_manifest()

elif command_name == "init":
    import os
    print("--- LMS Initialization Wizard ---")
    username = input("Enter username [lms]: ").strip()
    if not username:
        username = "lms"
        
    password = input("Enter password: ").strip()
    while not password:
        password = input("Password cannot be empty. Enter password: ").strip()
    
    source_name = input("Enter media source name: ").strip()
    while not source_name:
        source_name = input("Source name cannot be empty. Enter media source name: ").strip()
        
    source_path = input("Enter media source path: ").strip()
    while not source_path or not os.path.exists(source_path) or not os.path.isdir(source_path):
        if not source_path:
            source_path = input("Source path cannot be empty. Enter media source path: ").strip()
        else:
            source_path = input(f"Path '{source_path}' does not exist or is not a directory. Enter media source path: ").strip()
            
    # 1. Set password
    set_password(username, password)
    # 2. Add source
    add_source(source_name, source_path)
    # 3. Generate manifest
    generate_manifest()

else:
    print(f"Command '{command_name}' not found.")
    print_help()
