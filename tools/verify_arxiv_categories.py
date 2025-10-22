#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
arXivのカテゴリ略語が有効かどうかを確認するスクリプト
"""
import urllib.request
import urllib.error

# app.pyで定義されているtopics
topics = {
    "Physics": "",
    "Mathematics": "math",
    "Computer Science": "cs",
    "Quantitative Biology": "q-bio",
    "Quantitative Finance": "q-fin",
    "Statistics": "stat",
    "Electrical Engineering and Systems Science": "eess",
    "Economics": "econ"
}

physics_topics = {
    "Astrophysics": "astro-ph",
    "Condensed Matter": "cond-mat",
    "General Relativity and Quantum Cosmology": "gr-qc",
    "High Energy Physics - Experiment": "hep-ex",
    "High Energy Physics - Lattice": "hep-lat",
    "High Energy Physics - Phenomenology": "hep-ph",
    "High Energy Physics - Theory": "hep-th",
    "Mathematical Physics": "math-ph",
    "Nonlinear Sciences": "nlin",
    "Nuclear Experiment": "nucl-ex",
    "Nuclear Theory": "nucl-th",
    "Physics": "physics",
    "Quantum Physics": "quant-ph"
}

def verify_arxiv_category(abbr):
    """
    arXivの略語が有効かどうかを確認
    """
    if not abbr:
        return None, "Empty abbreviation"
    
    url = f"https://arxiv.org/list/{abbr}/new"
    try:
        response = urllib.request.urlopen(url)
        if response.status == 200:
            return True, url
        else:
            return False, f"Status: {response.status}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP Error {e.code}"
    except Exception as e:
        return False, str(e)

print("=" * 80)
print("arXiv Category Verification")
print("=" * 80)

print("\n[Topics]")
for name, abbr in topics.items():
    if not abbr:
        print(f"  {name:50s} : (skip - empty)")
        continue
    valid, info = verify_arxiv_category(abbr)
    status = "✅ VALID" if valid else "❌ INVALID"
    print(f"  {name:50s} : {abbr:10s} {status}")
    if not valid:
        print(f"    → {info}")

print("\n[Physics Topics]")
for name, abbr in physics_topics.items():
    valid, info = verify_arxiv_category(abbr)
    status = "✅ VALID" if valid else "❌ INVALID"
    print(f"  {name:50s} : {abbr:10s} {status}")
    if not valid:
        print(f"    → {info}")

print("\n" + "=" * 80)
print("Verification Complete")
print("=" * 80)
print("\n公式ドキュメント:")
print("  - Category Taxonomy: https://arxiv.org/category_taxonomy")
print("  - API Documentation: https://info.arxiv.org/help/api/user-manual.html")
print("  - Subject Classifications: https://info.arxiv.org/help/api/user-manual.html#subject_classifications")
