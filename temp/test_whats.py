import subprocess
result = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=15)
for line in result.stdout.strip().split("\n"):
    parts = line.strip().split(",")
    if len(parts) >= 1:
        name = parts[0].strip('"')
        if "whats" in name.lower() or "whats" in name.lower():
            print(f"RAW: [{name}] LOWER: [{name.lower()}]")
