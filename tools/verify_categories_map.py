#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
categories_mapのカテゴリ名が実際のarXiv論文データと一致するかを検証するスクリプト
"""
import sys
import io

# Windows環境でのUnicode出力対応
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, 'src')

from download_new_papers import get_papers
from relevancy import process_subject_fields

# app.pyで定義されているcategories_map
categories_map = {
    "Astrophysics": ["Astrophysics of Galaxies", "Cosmology and Nongalactic Astrophysics", "Earth and Planetary Astrophysics", "High Energy Astrophysical Phenomena", "Instrumentation and Methods for Astrophysics", "Solar and Stellar Astrophysics"],
    "Condensed Matter": ["Disordered Systems and Neural Networks", "Materials Science", "Mesoscale and Nanoscale Physics", "Other Condensed Matter", "Quantum Gases", "Soft Condensed Matter", "Statistical Mechanics", "Strongly Correlated Electrons", "Superconductivity"],
    "General Relativity and Quantum Cosmology": ["None"],
    "High Energy Physics - Experiment": ["None"],
    "High Energy Physics - Lattice": ["None"],
    "High Energy Physics - Phenomenology": ["None"],
    "High Energy Physics - Theory": ["None"],
    "Mathematical Physics": ["None"],
    "Nonlinear Sciences": ["Adaptation and Self-Organizing Systems", "Cellular Automata and Lattice Gases", "Chaotic Dynamics", "Exactly Solvable and Integrable Systems", "Pattern Formation and Solitons"],
    "Nuclear Experiment": ["None"],
    "Nuclear Theory": ["None"],
    "Physics": ["Accelerator Physics", "Applied Physics", "Atmospheric and Oceanic Physics", "Atomic and Molecular Clusters", "Atomic Physics", "Biological Physics", "Chemical Physics", "Classical Physics", "Computational Physics", "Data Analysis, Statistics and Probability", "Fluid Dynamics", "General Physics", "Geophysics", "History and Philosophy of Physics", "Instrumentation and Detectors", "Medical Physics", "Optics", "Physics and Society", "Physics Education", "Plasma Physics", "Popular Physics", "Space Physics"],
    "Quantum Physics": ["None"],
    "Mathematics": ["Algebraic Geometry", "Algebraic Topology", "Analysis of PDEs", "Category Theory", "Classical Analysis and ODEs", "Combinatorics", "Commutative Algebra", "Complex Variables", "Differential Geometry", "Dynamical Systems", "Functional Analysis", "General Mathematics", "General Topology", "Geometric Topology", "Group Theory", "History and Overview", "Information Theory", "K-Theory and Homology", "Logic", "Mathematical Physics", "Metric Geometry", "Number Theory", "Numerical Analysis", "Operator Algebras", "Optimization and Control", "Probability", "Quantum Algebra", "Representation Theory", "Rings and Algebras", "Spectral Theory", "Statistics Theory", "Symplectic Geometry"],
    "Computer Science": ["Artificial Intelligence", "Computation and Language", "Computational Complexity", "Computational Engineering, Finance, and Science", "Computational Geometry", "Computer Science and Game Theory", "Computer Vision and Pattern Recognition", "Computers and Society", "Cryptography and Security", "Data Structures and Algorithms", "Databases", "Digital Libraries", "Discrete Mathematics", "Distributed, Parallel, and Cluster Computing", "Emerging Technologies", "Formal Languages and Automata Theory", "General Literature", "Graphics", "Hardware Architecture", "Human-Computer Interaction", "Information Retrieval", "Information Theory", "Logic in Computer Science", "Machine Learning", "Mathematical Software", "Multiagent Systems", "Multimedia", "Networking and Internet Architecture", "Neural and Evolutionary Computing", "Numerical Analysis", "Operating Systems", "Other Computer Science", "Performance", "Programming Languages", "Robotics", "Social and Information Networks", "Software Engineering", "Sound", "Symbolic Computation", "Systems and Control"],
    "Quantitative Biology": ["Biomolecules", "Cell Behavior", "Genomics", "Molecular Networks", "Neurons and Cognition", "Other Quantitative Biology", "Populations and Evolution", "Quantitative Methods", "Subcellular Processes", "Tissues and Organs"],
    "Quantitative Finance": ["Computational Finance", "Economics", "General Finance", "Mathematical Finance", "Portfolio Management", "Pricing of Securities", "Risk Management", "Statistical Finance", "Trading and Market Microstructure"],
    "Statistics": ["Applications", "Computation", "Machine Learning", "Methodology", "Other Statistics", "Statistics Theory"],
    "Electrical Engineering and Systems Science": ["Audio and Speech Processing", "Image and Video Processing", "Signal Processing", "Systems and Control"],
    "Economics": ["Econometrics", "General Economics", "Theoretical Economics"]
}

topics = {
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

def verify_categories_for_topic(topic_name, abbr, expected_categories, limit=50):
    """
    指定したtopicの論文を取得して、実際に存在するカテゴリと比較
    """
    print(f"\n{'='*80}")
    print(f"Topic: {topic_name} ({abbr})")
    print(f"{'='*80}")
    
    try:
        # 論文を取得
        print(f"Fetching papers from arXiv (limit={limit})...")
        papers = get_papers(abbr, limit=limit)
        print(f"✓ Retrieved {len(papers)} papers")
        
        # 実際に現れたカテゴリを収集
        actual_categories = set()
        for paper in papers:
            subjects = paper.get('subjects', '')
            processed = process_subject_fields(subjects)
            actual_categories.update(processed)
        
        print(f"\n実際に見つかったカテゴリ数: {len(actual_categories)}")
        print(f"定義されているカテゴリ数: {len(expected_categories)}")
        
        # "None"は特殊ケース（サブカテゴリがない場合）
        if expected_categories == ["None"]:
            print("\n✓ このtopicはサブカテゴリを持たない定義です")
            print(f"  実際に存在するカテゴリ: {sorted(actual_categories)[:5]}...")
            return True, []
        
        # 定義されているが実際には見つからないカテゴリ
        missing = set(expected_categories) - actual_categories
        # 実際に存在するが定義されていないカテゴリ
        extra = actual_categories - set(expected_categories)
        
        # 結果表示
        if not missing and not extra:
            print("\n✅ 完全一致: すべてのカテゴリが正しく定義されています")
            return True, []
        
        issues = []
        
        if missing:
            print(f"\n⚠️  定義されているが見つからないカテゴリ ({len(missing)}件):")
            for cat in sorted(missing):
                print(f"    - {cat}")
                issues.append(f"Missing: {cat}")
        
        if extra:
            print(f"\n⚠️  実際に存在するが定義されていないカテゴリ ({len(extra)}件):")
            for cat in sorted(extra):
                print(f"    + {cat}")
                issues.append(f"Extra: {cat}")
        
        # サンプル論文のsubjectsを表示
        print(f"\n📄 サンプル論文のsubjectsフィールド (最初の3件):")
        for i, paper in enumerate(papers[:3], 1):
            subjects = paper.get('subjects', 'N/A')
            processed = process_subject_fields(subjects)
            print(f"  {i}. Raw: {subjects[:80]}...")
            print(f"     Processed: {processed}")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        print(f"\n❌ エラー: {str(e)}")
        return False, [f"Error: {str(e)}"]

print("=" * 80)
print("arXiv categories_map Verification")
print("=" * 80)
print("\n実際のarXiv論文データから各topicのカテゴリを検証します...")
print("注意: 少数の論文サンプルから検証するため、すべてのカテゴリが")
print("      見つからない場合があります。これは必ずしもエラーではありません。")

all_results = {}
total_issues = 0

# 各topicを検証
for topic_name, categories in categories_map.items():
    # 対応するabbrを取得
    if topic_name in topics:
        abbr = topics[topic_name]
    elif topic_name in physics_topics:
        abbr = physics_topics[topic_name]
    else:
        print(f"\n⚠️  Skip: {topic_name} (abbreviation not found)")
        continue
    
    valid, issues = verify_categories_for_topic(topic_name, abbr, categories, limit=30)
    all_results[topic_name] = (valid, issues)
    total_issues += len(issues)

# 総括
print("\n" + "=" * 80)
print("Verification Summary")
print("=" * 80)

perfect = 0
warnings = 0
for topic_name, (valid, issues) in all_results.items():
    if valid:
        status = "✅ OK"
        perfect += 1
    else:
        status = f"⚠️  {len(issues)} issues"
        warnings += 1
    print(f"  {topic_name:50s} : {status}")

print(f"\n総計: {perfect}件OK, {warnings}件に警告")
print(f"合計問題数: {total_issues}")

print("\n" + "=" * 80)
print("Note:")
print("  - 少数サンプルでの検証のため、すべてのカテゴリが見つからない可能性があります")
print("  - 「定義されているが見つからない」カテゴリは、頻度が低いだけかもしれません")
print("  - 「実際に存在するが定義されていない」カテゴリは追加を検討してください")
print("=" * 80)
