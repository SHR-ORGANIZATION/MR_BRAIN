import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from agent import smart_parse_command, extract_file_name

tests = [
    "create file named mydocument in volume (D:)",
    "create file test on drive E",
    "create file data in local disk D",
    "create file notes on volume (C:)",
    "make folder backup in drive (F:)",
]

for t in tests:
    parsed = smart_parse_command(t)
    path = extract_file_name(t)
    print(f"  Command:  {t}")
    print(f"  Entity:   {parsed['entity']}")
    print(f"  Base Dir: {parsed['base_dir']}")
    print(f"  File:     {path}")
    print()
