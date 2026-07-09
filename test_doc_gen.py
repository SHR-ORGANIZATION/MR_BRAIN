#!/usr/bin/env python
"""Test document generation improvements."""
from agent import process_command

tests = [
    "write a document about AI",
    "create pdf named myreport about machine learning",
    "write excel spreadsheet about sales data",
    "WRITE THE PDF DOC THEN NAME IT AS SHAKIRA ALSO WRITE CONTENT ABOUT YOU",
]

for cmd in tests:
    print(f"\n{'='*60}")
    print(f"Command: {cmd}")
    r = process_command(cmd)
    print(f"Status: {r.get('status')}")
    print(f"Message: {r.get('message')[:150]}")
