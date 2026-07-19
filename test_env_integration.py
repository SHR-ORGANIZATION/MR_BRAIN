"""Quick test to verify environment scanner integration works."""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.environment_scanner import get_scanner, get_environment_stats, initialize_environment
from automation.app_tasks import open_application

# Initialize environment (normally done by agent.py at startup)
initialize_environment()

print("=" * 60)
print("Testing AMAZON Environment Integration")
print("=" * 60)

# Check scanner is initialized
scanner = get_scanner()
stats = get_environment_stats()
print(f"\nEnvironment Stats: {stats}")

# Test finding apps
test_apps = ["brave", "vscode", "chrome", "docker", "postman", "notepad"]
print("\nApp Discovery Test:")
for app in test_apps:
    info = scanner.find_app(app)
    if info:
        print(f"  {app:12} -> {info['display_name']}")
    else:
        print(f"  {app:12} -> NOT FOUND")

# Test opening an app (just show what would be launched)
print("\nSimulating 'open brave':")
result = open_application("brave")
print(f"  Status: {result['status']}")
print(f"  Message: {result['message']}")

print("\nSimulating 'open vscode':")
result = open_application("vscode")
print(f"  Status: {result['status']}")
print(f"  Message: {result['message']}")

print("\nSimulating 'open notepad':")
result = open_application("notepad")
print(f"  Status: {result['status']}")
print(f"  Message: {result['message']}")

print("\nSimulating 'open docker' (not in test list but should be found):")
result = open_application("docker")
print(f"  Status: {result['status']}")
print(f"  Message: {result['message']}")

print("\n" + "=" * 60)
print("Integration Test Complete!")
print("=" * 60)