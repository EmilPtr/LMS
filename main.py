import sys
from config import *
from gen_manifest import *

arguments = sys.argv[1:]

if len(arguments) < 1:
    print("Incorrect usage, type 'lms help' for list of available commands.")
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


elif command_name == "generate":
    manifest = generate_manifest()

else:
    print("Command not found, type 'lms help' for list of available commands.")
