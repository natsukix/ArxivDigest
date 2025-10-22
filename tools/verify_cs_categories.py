#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
categories_mapの検証: Computer Scienceカテゴリを実際のarXivデータと照合
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from download_new_papers import get_papers
from relevancy import process_subject_fields

# app.pyのComputer Scienceカテゴリ定義
CS_CATEGORIES = [
    "Artificial Intelligence",
    "Computation and Language",
    "Computational Complexity",
    "Computational Engineering, Finance, and Science",
    "Computational Geometry",
    "Computer Science and Game Theory",
    "Computer Vision and Pattern Recognition",
    "Computers and Society",
    "Cryptography and Security",
    "Data Structures and Algorithms",
    "Databases",
    "Digital Libraries",
    "Discrete Mathematics",
    "Distributed, Parallel, and Cluster Computing",
    "Emerging Technologies",
    "Formal Languages and Automata Theory",
    "General Literature",
    "Graphics",
    "Hardware Architecture",
    "Human-Computer Interaction",
    "Information Retrieval",
    "Information Theory",
    "Logic in Computer Science",
    "Machine Learning",
    "Mathematical Software",
    "Multiagent Systems",
    "Multimedia",
    "Networking and Internet Architecture",
    "Neural and Evolutionary Computing",
    "Numerical Analysis",
    "Operating Systems",
    "Other Computer Science",
    "Performance",
    "Programming Languages",
    "Robotics",
    "Social and Information Networks",
    "Software Engineering",
    "Sound",
    "Symbolic Computation",
    "Systems and Control"
]

print("="*80)
print("Computer Science Categories Verification")
print("="*80)

print(f"\n[1] Fetching papers from arXiv (cs)...")
papers = get_papers('cs', limit=100)
print(f"    Retrieved: {len(papers)} papers")

print(f"\n[2] Extracting actual categories from papers...")
actual_categories = set()
category_counts = {}

for paper in papers:
    subjects = paper.get('subjects', '')
    processed = process_subject_fields(subjects)
    for cat in processed:
        actual_categories.add(cat)
        category_counts[cat] = category_counts.get(cat, 0) + 1

print(f"    Found: {len(actual_categories)} unique categories")

print(f"\n[3] Comparing with defined categories...")
defined_set = set(CS_CATEGORIES)
actual_cs_only = {cat for cat in actual_categories if cat in defined_set or any(cs_cat in cat for cs_cat in ['Computer', 'Computation'])}

missing_in_actual = defined_set - actual_categories
extra_in_actual = actual_cs_only - defined_set

print(f"\n--- Results ---")
print(f"Defined categories: {len(CS_CATEGORIES)}")
print(f"Found categories (CS-related): {len(actual_cs_only)}")
print(f"Perfect matches: {len(defined_set & actual_categories)}")

if missing_in_actual:
    print(f"\n[WARNING] Defined but NOT found in sample ({len(missing_in_actual)} categories):")
    print("  (These might be valid but just rare in this sample)")
    for cat in sorted(missing_in_actual):
        print(f"    - {cat}")

if extra_in_actual:
    print(f"\n[INFO] Found but NOT defined ({len(extra_in_actual)} categories):")
    print("  (Consider adding these to categories_map)")
    for cat in sorted(extra_in_actual):
        count = category_counts.get(cat, 0)
        print(f"    + {cat} ({count} papers)")

print(f"\n[4] Top 20 most common categories in sample:")
sorted_cats = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
for cat, count in sorted_cats[:20]:
    status = "OK" if cat in defined_set else "NOT DEFINED"
    print(f"    {count:3d} papers | {status:12s} | {cat}")

print("\n" + "="*80)
print("Conclusion:")
if not missing_in_actual and not extra_in_actual:
    print("  [OK] All categories are correctly defined!")
elif not extra_in_actual:
    print("  [OK] All found categories are defined (some defined ones not found in sample)")
else:
    print("  [REVIEW] Some categories found in actual data are not defined")
    print("           Consider updating categories_map in app.py")
print("="*80)

# 公式ドキュメント
print("\nOfficial arXiv Category Reference:")
print("  https://arxiv.org/category_taxonomy")
print("  https://arxiv.org/archive/cs")
