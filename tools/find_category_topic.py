#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
カテゴリ名から、それがどのトピックに属するかを検索するツール
"""
import sys
import io

# Windows環境でのUnicode出力対応
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# app.pyのcategories_mapをインポート
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

def find_topic_for_category(category_name):
    """
    カテゴリ名から所属するトピックを検索
    """
    results = []
    for topic, categories in categories_map.items():
        if category_name in categories:
            results.append(topic)
    return results

def search_category_fuzzy(search_term):
    """
    部分一致でカテゴリを検索
    """
    results = []
    search_lower = search_term.lower()
    for topic, categories in categories_map.items():
        for category in categories:
            if search_lower in category.lower():
                results.append((topic, category))
    return results

# インタラクティブモード
if __name__ == "__main__":
    print("=" * 80)
    print("カテゴリ → トピック 検索ツール")
    print("=" * 80)
    
    if len(sys.argv) > 1:
        # コマンドライン引数から検索
        query = " ".join(sys.argv[1:])
        print(f"\n検索: '{query}'")
        
        # 完全一致検索
        topics = find_topic_for_category(query)
        if topics:
            print(f"\n✅ 完全一致:")
            for topic in topics:
                print(f"  トピック: {topic}")
                print(f"  カテゴリ: {query}")
        else:
            print(f"\n❌ 完全一致なし")
        
        # 部分一致検索
        fuzzy_results = search_category_fuzzy(query)
        if fuzzy_results:
            print(f"\n💡 部分一致 ({len(fuzzy_results)}件):")
            for topic, category in fuzzy_results[:10]:
                print(f"  トピック: {topic:45s} | カテゴリ: {category}")
            if len(fuzzy_results) > 10:
                print(f"  ... 他 {len(fuzzy_results) - 10} 件")
    else:
        # インタラクティブモード
        print("\n使い方:")
        print("  python find_category_topic.py <カテゴリ名>")
        print("\n例:")
        print("  python find_category_topic.py 'Artificial Intelligence'")
        print("  python find_category_topic.py 'Machine Learning'")
        print("  python find_category_topic.py 'Systems and Control'")
        print("  python find_category_topic.py 'Number Theory'")
        print("\n部分一致検索も可能:")
        print("  python find_category_topic.py Intelligence")
        print("  python find_category_topic.py Control")
        
        print("\n" + "=" * 80)
        print("よく検索されるカテゴリ:")
        print("=" * 80)
        
        common_categories = [
            "Artificial Intelligence",
            "Machine Learning",
            "Computer Vision and Pattern Recognition",
            "Computation and Language",
            "Systems and Control",
            "Number Theory",
            "Optimization and Control",
            "Neurons and Cognition"
        ]
        
        for cat in common_categories:
            topics = find_topic_for_category(cat)
            if topics:
                print(f"  {cat:45s} → {', '.join(topics)}")
            else:
                print(f"  {cat:45s} → (見つかりません)")
    
    print("\n" + "=" * 80)
