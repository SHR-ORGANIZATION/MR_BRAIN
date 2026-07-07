import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from agent import process_command

print("=== which apps are running ===\n")
r = process_command("which apps are running")
print(r.get("message"))
