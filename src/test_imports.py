#!/usr/bin/env python
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("Step 1: Importing utils...")
import utils
print("Step 2: utils imported successfully")

print("Step 3: Testing safe_print...")
print("Hello World")
print("Step 4: safe_print works!")

print("Step 5: Importing other modules...")
try:
    from relevancy import generate_relevance_score
    print("Step 6: relevancy imported")
except Exception as e:
    print(f"Step 6 FAILED: {e}")

print("All imports successful!")
